import docker
import time
import logging
import os
import threading
from app.core.config import DOCKER_DIR, MODELS_DIR

logger = logging.getLogger(__name__)

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            self.client = None

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

    def start_model(self, model):
        if not self.client:
            return None
            
        models_dir = str(MODELS_DIR)
        model_path = os.path.join(models_dir, model.gguf_filename)
        
        if not os.path.exists(model_path):
            logger.info(f"Model file {model.gguf_filename} not found. Triggering background download.")
            from app.services.huggingface_downloader import downloader
            threading.Thread(target=downloader.download_model, args=(model.id,)).start()
            return "downloading"
            
        image_tag = self.build_llama_image(model.llamacpp_version_hash)
        container_name = f"plam-model-{model.id}"
        
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
            remove=True,
            device_requests=[docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])]
        )
        logger.info(f"Started model {model.name} in container {container_name}")
        return container

    def stop_model(self, model_id: str):
        if not self.client:
            return
            
        container_name = f"plam-model-{model_id}"
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped model container {container_name}")
        except docker.errors.NotFound:
            pass

docker_manager = DockerManager()
