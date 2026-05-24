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

def test_get_db_coverage():
    from app.db.database import get_db
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    try:
        next(db_gen)
    except StopIteration:
        pass

def test_websocket_metrics():
    with client.websocket_connect("/ws/metrics") as websocket:
        data = websocket.receive_text()
        import json
        metrics = json.loads(data)
        assert "cpu_percent" in metrics
