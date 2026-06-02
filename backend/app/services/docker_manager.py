import docker
import time
import logging
import os
import threading
import struct
import fcntl
from uuid import UUID
from multiprocessing.shared_memory import SharedMemory
from app.core.config import DOCKER_DIR, MODELS_DIR
from app.services.resource_manager import resource_manager
from app.services.huggingface_downloader import downloader

logger = logging.getLogger(__name__)

class SharedActiveStreamsRegistry:
    def __init__(self):
        # Place lockfile in MODELS_DIR parent to remain within workspace
        self.lockfile_path = os.path.join(MODELS_DIR.parent, ".plam_shm.lock")
        # Ensure file exists
        with open(self.lockfile_path, "a") as f:
            pass
        self._lockfile = open(self.lockfile_path, "r+")
        
        self.shm_name = "plam_shared_active_streams"
        self.shm_size = 4096
        self._shm = None
        self._init_shm()

    def _init_shm(self):
        try:
            self._shm = SharedMemory(name=self.shm_name, create=False)
        except FileNotFoundError:
            try:
                self._shm = SharedMemory(name=self.shm_name, create=True, size=self.shm_size)
                # Initialize count of entries to 0
                self._shm.buf[:4] = struct.pack(">I", 0)
            except Exception:
                # Concurrent creation race: try attaching again
                try:
                    self._shm = SharedMemory(name=self.shm_name, create=False)
                except Exception as e:
                    logger.error(f"Failed to initialize SharedMemory: {e}")
                    self._shm = None

    def _lock(self):
        fcntl.flock(self._lockfile, fcntl.LOCK_EX)

    def _unlock(self):
        fcntl.flock(self._lockfile, fcntl.LOCK_UN)

    def _read_all(self) -> dict[UUID, int]:
        if not self._shm:
            return {}
        try:
            num_entries = struct.unpack(">I", self._shm.buf[:4])[0]
            entries = {}
            for i in range(num_entries):
                offset = 4 + i * 24
                uuid_bytes = bytes(self._shm.buf[offset:offset+16])
                count = struct.unpack(">Q", self._shm.buf[offset+16:offset+24])[0]
                if uuid_bytes != b'\x00' * 16:
                    entries[UUID(bytes=uuid_bytes)] = count
            return entries
        except Exception as e:
            logger.error(f"Error reading shared memory: {e}")
            return {}

    def _write_all(self, entries: dict[UUID, int]):
        if not self._shm:
            return
        try:
            num_entries = len(entries)
            self._shm.buf[:4] = struct.pack(">I", num_entries)
            for i, (model_id, count) in enumerate(entries.items()):
                offset = 4 + i * 24
                self._shm.buf[offset:offset+16] = model_id.bytes
                self._shm.buf[offset+16:offset+24] = struct.pack(">Q", count)
        except Exception as e:
            logger.error(f"Error writing shared memory: {e}")

    def increment(self, model_id: UUID):
        self._lock()
        try:
            entries = self._read_all()
            entries[model_id] = entries.get(model_id, 0) + 1
            self._write_all(entries)
            logger.info(f"Shared Memory: Model {model_id} active streams incremented to {entries[model_id]}")
        finally:
            self._unlock()

    def decrement(self, model_id: UUID):
        self._lock()
        try:
            entries = self._read_all()
            if model_id in entries:
                entries[model_id] = max(0, entries[model_id] - 1)
                if entries[model_id] == 0:
                    del entries[model_id]
            self._write_all(entries)
            logger.info(f"Shared Memory: Model {model_id} active streams decremented")
        finally:
            self._unlock()

    def is_in_use(self, model_id: UUID) -> bool:
        self._lock()
        try:
            entries = self._read_all()
            in_use = entries.get(model_id, 0) > 0
            return in_use
        finally:
            self._unlock()

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            self.client = None
        self._active_registry = SharedActiveStreamsRegistry()

    def increment_active_stream(self, model_id: UUID):
        self._active_registry.increment(model_id)

    def decrement_active_stream(self, model_id: UUID):
        self._active_registry.decrement(model_id)

    def is_model_in_use(self, model_id: UUID) -> bool:
        return self._active_registry.is_in_use(model_id)

    def get_model_container(self, model_id: UUID):
        if not self.client:
            return None
        container_name = f"plam-model-{model_id}"
        try:
            return self.client.containers.get(container_name)
        except Exception:
            return None

    def get_model_id_from_container_name(self, container_name: str) -> UUID | None:
        """
        Extracts and validates the model UUID from a container name.
        """
        if not container_name or not container_name.startswith("plam-model-"):
            return None
        model_id_str = container_name.replace("plam-model-", "")
        try:
            return UUID(model_id_str)
        except ValueError:
            return None

    def _evict_active_models_for_ram(self, required_ram_mb: int, current_container_name: str) -> bool:
        """
        Stops running model containers sequentially to free up RAM until required_ram_mb is available.
        Returns True if memory allocation is successful, False otherwise.
        """
        if resource_manager.can_allocate(required_ram_mb):
            return True
            
        logger.info(f"Insufficient RAM. Freeing running models to allocate {required_ram_mb}MB...")
        try:
            for container in self.client.containers.list():
                if container.name == current_container_name:
                    continue
                    
                other_model_uuid = self.get_model_id_from_container_name(container.name)
                if not other_model_uuid:
                    continue
                    
                if self.is_model_in_use(other_model_uuid):
                    logger.info(f"Model {other_model_uuid} is currently in use by an active stream, skipping eviction.")
                    continue
                    
                logger.info(f"Stopping model {other_model_uuid} to free RAM...")
                self.stop_model(str(other_model_uuid))
                time.sleep(1.0)
                if resource_manager.can_allocate(required_ram_mb):
                    return True
        except Exception as e:
            logger.error(f"Error while freeing RAM: {e}")
            
        return resource_manager.can_allocate(required_ram_mb)

    def start_db(self):
        if not self.client:
            logger.warning("Docker client not available. Cannot start PostgreSQL container.")
            return
        
        container_name = "plam-postgres"
        try:
            container = self.client.containers.get(container_name)
            if container.status != "running":
                logger.info(f"Starting existing container {container_name}...")
                container.start()
            else:
                logger.info(f"Container {container_name} is already running.")
        except docker.errors.NotFound:
            logger.info(f"Creating and starting new container {container_name}...")
            # We need pgvector. 'ankane/pgvector' is the standard pgvector image.
            container = self.client.containers.run(
                "ankane/pgvector:latest",
                name=container_name,
                environment={
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "postgres",
                    "POSTGRES_DB": "plam"
                },
                ports={"5432/tcp": 15432},
                detach=True,
                remove=False
            )
        
        # Wait a bit for postgres to be ready
        logger.info("Waiting for PostgreSQL to be ready...")
        time.sleep(3)
        logger.info("PostgreSQL container initialization triggered.")

    def build_llama_image(self, version_hash: str):
        if not self.client:
            return None
            
        image_tag = f"plam/llama.cpp:{version_hash}"
        dockerfile_path = str(DOCKER_DIR)
        
        try:
            self.client.images.get(image_tag)
            return image_tag
        except docker.errors.ImageNotFound:
            logger.info(f"Building {image_tag} from {dockerfile_path}...")
            image, build_logs = self.client.images.build(
                path=dockerfile_path,
                dockerfile="Dockerfile.llamacpp",
                tag=image_tag,
                buildargs={"LLAMACPP_VERSION_HASH": version_hash},
                rm=True
            )
            return image_tag

    def start_model(self, model, wait=True):
        if not self.client:
            raise RuntimeError("Docker daemon is not running or accessible. Please start Docker and try again.")
            
        container_name = f"plam-model-{model.id}"
        
        # 1. Idempotency check: return container if already running
        try:
            container = self.client.containers.get(container_name)
            if container.status == "running":
                logger.info(f"Model container {container_name} is already running.")
                return container
            else:
                logger.info(f"Removing stopped container {container_name}...")
                container.remove(force=True)
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error checking/removing pre-existing container: {e}")

        models_dir = str(MODELS_DIR)
        model_path = os.path.join(models_dir, model.gguf_filename)
        
        if not os.path.exists(model_path):
            logger.info(f"Model file {model.gguf_filename} not found. Triggering background download.")
            threading.Thread(target=downloader.download_model, args=(model.id,)).start()
            return "downloading"
            
        # 2. Enforce memory availability: stop other models if system memory is low
        if not self._evict_active_models_for_ram(model.ram_required_mb, container_name):
            raise RuntimeError(
                f"Insufficient system memory to launch model {model.name} (Requires {model.ram_required_mb} MB). "
                "All other active models are currently in use and cannot be stopped."
            )

        image_tag = self.build_llama_image(model.llamacpp_version_hash)
        
        cmd = [
            "--model", f"/models/{model.gguf_filename}",
            "--ctx-size", str(model.context_size),
            "--port", "8000",
            "--host", "0.0.0.0"
        ]
        
        if model.llamacpp_args:
            for k, v in model.llamacpp_args.items():
                if not k.startswith('-'):
                    k = f"--{k}"
                
                if isinstance(v, bool):
                    if v:
                        cmd.append(k)
                else:
                    cmd.extend([k, str(v)])
        
        container = self.client.containers.run(
            image_tag,
            name=container_name,
            command=cmd,
            volumes={models_dir: {'bind': '/models', 'mode': 'ro'}},
            ports={"8000/tcp": None},
            detach=True,
            remove=False, # Changed to False so we can fetch logs if it crashes immediately
            device_requests=[docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])]
        )
        logger.info(f"Started model {model.name} in container {container_name}")
        
        if wait:
            logger.info(f"Waiting for model container {container_name} to be fully running and bound...")
            for _ in range(30):
                try:
                    container.reload()
                    if container.status == "running":
                        port_data = container.attrs["NetworkSettings"]["Ports"].get("8000/tcp")
                        if port_data:
                            host_port = int(port_data[0]["HostPort"])
                            import http.client
                            try:
                                conn = http.client.HTTPConnection("127.0.0.1", host_port, timeout=0.5)
                                conn.request("GET", "/health")
                                resp = conn.getresponse()
                                resp.read()  # Read response body to clean up connection
                                conn.close()
                                break
                            except Exception:
                                pass
                    elif container.status in ["exited", "dead"]:
                        logs = container.logs(tail=15).decode("utf-8", errors="replace")
                        logger.error(
                            f"Model container failed to start and exited with status '{container.status}'.\n\n"
                            f"Container Logs:\n{logs}"
                        )
                        try:
                            container.remove(force=True)
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"Model container failed to start and exited with status '{container.status}'.\n\n"
                            f"Container Logs:\n{logs}"
                        )
                except RuntimeError:
                    raise
                except Exception:
                    pass
                time.sleep(0.5)
                
        return container

    def stop_model(self, model_id: str):
        if not self.client:
            return
            
        container_name = f"plam-model-{model_id}"
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove(force=True)
            logger.info(f"Stopped and removed model container {container_name}")
        except docker.errors.NotFound:
            pass

docker_manager = DockerManager()
