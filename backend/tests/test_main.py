import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

@patch('app.main.docker_manager')
def test_read_root(mock_docker_manager):
    # Mock the start_db method to prevent docker container spin-up during unit tests
    mock_docker_manager.start_db.return_value = None
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "PLAM Backend running"}
