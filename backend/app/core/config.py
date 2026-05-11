import os
from pathlib import Path
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
DOCKER_DIR = BACKEND_DIR / "docker"

class Settings(BaseSettings):
    PROJECT_NAME: str = "PLAM API"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "plam"
    POSTGRES_PORT: str = "15432"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
