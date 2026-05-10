import docker
import time
import logging

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

docker_manager = DockerManager()
