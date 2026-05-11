import pytest
import uuid
from unittest.mock import patch, MagicMock
from app.services.resource_manager import resource_manager
from app.services.docker_manager import docker_manager
from app.models.domain import LLMModel

def test_resource_manager_metrics():
    metrics = resource_manager.get_system_metrics()
    assert "cpu_percent" in metrics
    assert "ram_total_mb" in metrics
    assert "ram_free_mb" in metrics

@patch('psutil.virtual_memory')
def test_resource_manager_can_allocate(mock_vm):
    # Mock psutil.virtual_memory to return a MagicMock with available memory
    mock_mem = MagicMock()
    mock_mem.available = 12 * 1024 * 1024 * 1024 # 12 GB free
    mock_vm.return_value = mock_mem
    
    # Require 1GB (1024MB), leaves ~11GB free > 10GB MIN -> True
    assert resource_manager.can_allocate(1024) == True
    
    # Require 3GB (3072MB), leaves ~9GB free < 10GB MIN -> False
    assert resource_manager.can_allocate(3072) == False

@patch('app.services.docker_manager.os.path.exists')
@patch('app.services.docker_manager.DockerManager.build_llama_image')
def test_start_model(mock_build, mock_exists):
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True
    
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048
    )
    
    with patch.object(docker_manager, 'client') as mock_client:
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container
        
        container = docker_manager.start_model(model)
        
        mock_client.containers.run.assert_called_once()
        assert container == mock_container

def test_stop_model():
    with patch.object(docker_manager, 'client') as mock_client:
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        
        docker_manager.stop_model("123")
        
        mock_client.containers.get.assert_called_once_with("plam-model-123")
        mock_container.stop.assert_called_once()
