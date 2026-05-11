from unittest.mock import patch

def test_create_model(client):
    response = client.post(
        "/models/",
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
    response = client.get("/models/")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_update_model(client):
    # First get the model
    response = client.get("/models/")
    model_id = response.json()[0]["id"]
    
    # Update it
    update_res = client.put(
        f"/models/{model_id}",
        json={"context_size": 16384}
    )
    assert update_res.status_code == 200
    assert update_res.json()["context_size"] == 16384

@patch('app.api.endpoints.models.downloader.download_model')
def test_download_model(mock_download, client):
    response = client.get("/models/")
    model_id = response.json()[0]["id"]
    
    dl_res = client.post(f"/models/{model_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.json()["status"] == "downloading"

def test_delete_model(client):
    response = client.get("/models/")
    model_id = response.json()[0]["id"]
    
    del_res = client.delete(f"/models/{model_id}")
    assert del_res.status_code == 200
    
    # Verify deletion
    get_res = client.get(f"/models/{model_id}")
    assert get_res.status_code == 404
