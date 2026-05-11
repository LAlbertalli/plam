import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.db.database import Base, get_db
from app.core.config import settings
from app.services.docker_manager import docker_manager

# Ensure postgres is running before tests
docker_manager.start_db()

# Create test database if it doesn't exist
admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

with admin_engine.connect() as conn:
    try:
        conn.execute(text("CREATE DATABASE plam_test"))
    except Exception:
        pass

TEST_DB_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/plam_test"
engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Run migrations / create tables in test DB
    Base.metadata.create_all(bind=engine)
    yield
    # We could drop tables here, but dropping DB is faster or just truncate
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with patch('app.main.docker_manager.start_db'):
        with TestClient(app) as c:
            yield c
