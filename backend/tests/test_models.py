from unittest.mock import patch

def test_create_model(client):
    response = client.post(
        "/api/v1/models/",
        json={
            "name": "Llama-3-8B",
            "hf_repo_id": "meta-llama/Meta-Llama-3-8B-Instruct-GGUF",
            "gguf_filename": "llama3.gguf",
            "ram_required_mb": 8000,
            "context_size": 8192
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Llama-3-8B"
    assert "id" in data
    assert data["status"] == "stopped"

def test_get_models(client):
    response = client.get("/api/v1/models/")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_update_model(client):
    # First get the model
    response = client.get("/api/v1/models/")
    model_id = response.json()[0]["id"]
    
    # Update it
    update_res = client.put(
        f"/api/v1/models/{model_id}",
        json={"context_size": 16384}
    )
    assert update_res.status_code == 200
    assert update_res.json()["context_size"] == 16384

@patch('app.api.endpoints.models.downloader.download_model')
def test_download_model(mock_download, client):
    response = client.get("/api/v1/models/")
    model_id = response.json()[0]["id"]
    
    dl_res = client.post(f"/api/v1/models/{model_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.json()["status"] == "downloading"

def test_delete_model(client):
    response = client.get("/api/v1/models/")
    model_id = response.json()[0]["id"]
    
    del_res = client.delete(f"/api/v1/models/{model_id}")
    assert del_res.status_code == 200
    
    # Verify deletion
    get_res = client.get(f"/api/v1/models/{model_id}")
    assert get_res.status_code == 404

def test_download_model_error(client):
    from app.services.huggingface_downloader import downloader
    # First create a temporary model configuration
    create_res = client.post(
        "/api/v1/models/",
        json={
            "name": "ErrorModel",
            "hf_repo_id": "invalid/invalid-repo",
            "gguf_filename": "invalid.gguf",
            "ram_required_mb": 1000,
            "context_size": 2048
        }
    )
    assert create_res.status_code == 200
    model_id = create_res.json()["id"]

    # Mock the downloader to return an error for this model
    with patch.object(downloader, 'get_error', return_value="Invalid repository name"):
        get_res = client.get(f"/api/v1/models/{model_id}")
        assert get_res.status_code == 200
        assert get_res.json()["error_message"] == "Invalid repository name"

