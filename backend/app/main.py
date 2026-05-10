import logging
from fastapi import FastAPI
from app.core.config import settings
from app.services.docker_manager import docker_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def startup_event():
    logger.info("Starting up PLAM Backend...")
    docker_manager.start_db()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "PLAM Backend running"}
