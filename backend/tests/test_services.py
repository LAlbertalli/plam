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
@patch('app.services.resource_manager.resource_manager.can_allocate')
@patch('app.services.docker_manager.time.sleep')
def test_start_model(mock_sleep, mock_can_allocate, mock_build, mock_exists):
    mock_can_allocate.return_value = True
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True
    
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=1000
    )
    
    with patch.object(docker_manager, 'client') as mock_client:
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container
        
        # Mock get to raise NotFound
        import docker
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        
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

@patch('app.services.docker_manager.os.path.exists')
@patch('app.services.docker_manager.DockerManager.build_llama_image')
@patch('app.services.resource_manager.resource_manager.can_allocate')
@patch('app.services.docker_manager.time.sleep')
def test_start_model_insufficient_ram_stops_other_models(mock_sleep, mock_can_allocate, mock_build, mock_exists):
    # First check fails (insufficient RAM), second and third checks succeed (RAM freed after stopping other model)
    mock_can_allocate.side_effect = [False, True, True]
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True
    
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=2048
    )
    
    other_model_id = uuid.uuid4()
    with patch.object(docker_manager, 'client') as mock_client:
        mock_other_container = MagicMock()
        mock_other_container.name = f"plam-model-{other_model_id}"
        mock_client.containers.list.return_value = [mock_other_container]
        
        mock_target_container = MagicMock()
        mock_client.containers.run.return_value = mock_target_container
        
        # When get is called on container check, raise NotFound so it thinks it isn't running
        import docker
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        
        # Stop model mock
        with patch.object(docker_manager, 'stop_model') as mock_stop:
            container = docker_manager.start_model(model)
            
            # Assert that stop_model was called to evict the other running container
            mock_stop.assert_called_once_with(str(other_model_id))
            # Target container should successfully run
            mock_client.containers.run.assert_called_once()
            assert container == mock_target_container

@patch('app.services.docker_manager.os.path.exists')
@patch('app.services.docker_manager.DockerManager.build_llama_image')
@patch('app.services.resource_manager.resource_manager.can_allocate')
@patch('app.services.docker_manager.time.sleep')
def test_start_model_skips_in_use_models_for_eviction(mock_sleep, mock_can_allocate, mock_build, mock_exists):
    # Enforce insufficient RAM (keeps returning False)
    mock_can_allocate.return_value = False
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True
    
    other_model_id = uuid.uuid4()
    
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=2048
    )
    
    # Mark the other model as in use
    docker_manager.increment_active_stream(other_model_id)
    
    try:
        with patch.object(docker_manager, 'client') as mock_client:
            mock_other_container = MagicMock()
            mock_other_container.name = f"plam-model-{other_model_id}"
            mock_client.containers.list.return_value = [mock_other_container]
            
            # When get is called on container check, raise NotFound so it thinks it isn't running
            import docker
            mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
            
            with patch.object(docker_manager, 'stop_model') as mock_stop:
                # Should raise RuntimeError since the only running model is in use and cannot be stopped
                with pytest.raises(RuntimeError) as exc_info:
                    docker_manager.start_model(model)
                
                assert "All other active models are currently in use" in str(exc_info.value)
                # Ensure stop_model was NEVER called for the in-use model
                mock_stop.assert_not_called()
    finally:
        docker_manager.decrement_active_stream(other_model_id)

from tests.conftest import TestingSessionLocal
from app.services.orchestrator_service import orchestrator_service
from app.models.domain import Session as ChatSession, Agent, LLMModel, ShortTermMemory

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.query(ShortTermMemory).delete()
        db.query(ChatSession).delete()
        db.query(Agent).delete()
        db.query(LLMModel).delete()
        db.commit()
        db.close()


def test_parse_thought_and_save_response(db_session):
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    agent = Agent(
        id=uuid.uuid4(),
        name="TestAgent",
        model_id=model.id,
        system_prompt="Prompt"
    )
    db_session.add(agent)
    db_session.commit()

    session = ChatSession(
        id=uuid.uuid4(),
        title="Session"
    )
    db_session.add(session)
    db_session.commit()

    # 1. Test standard <thought> tags
    raw_thought = "<thought>Thinking details</thought>This is the actual answer."
    content, trace = orchestrator_service._parse_thought_and_save_response(
        session.id, agent.id, 1, raw_thought, model.id, db_session
    )
    assert content == "This is the actual answer."
    assert trace == "Thinking details"

def test_start_model_no_docker_client():
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=1000
    )
    # Temporary mock client to None
    with patch.object(docker_manager, 'client', None):
        with pytest.raises(RuntimeError) as exc_info:
            docker_manager.start_model(model)
        assert "Docker daemon is not running or accessible" in str(exc_info.value)

@patch('app.services.docker_manager.os.path.exists')
@patch('app.services.docker_manager.DockerManager.build_llama_image')
@patch('app.services.resource_manager.resource_manager.can_allocate')
@patch('app.services.docker_manager.time.sleep')
def test_start_model_container_crashes(mock_sleep, mock_can_allocate, mock_build, mock_exists):
    mock_can_allocate.return_value = True
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True
    
    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=1000
    )
    
    with patch.object(docker_manager, 'client') as mock_client:
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_container.logs.return_value = b"CUDA error: out of memory"
        mock_client.containers.run.return_value = mock_container
        
        # Mock get to raise NotFound
        import docker
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        
        with pytest.raises(RuntimeError) as exc_info:
            docker_manager.start_model(model)
            
        assert "Model container failed to start and exited" in str(exc_info.value)
        assert "CUDA error: out of memory" in str(exc_info.value)
        mock_container.remove.assert_called_once_with(force=True)

@patch('app.services.docker_manager.os.path.exists')
@patch('app.services.docker_manager.DockerManager.build_llama_image')
@patch('app.services.resource_manager.resource_manager.can_allocate')
@patch('app.services.docker_manager.time.sleep')
@patch('http.client.HTTPConnection')
def test_start_model_success_with_http_check(mock_http_class, mock_sleep, mock_can_allocate, mock_build, mock_exists):
    mock_can_allocate.return_value = True
    mock_build.return_value = "plam/llama.cpp:test_hash"
    mock_exists.return_value = True

    model = LLMModel(
        id=uuid.uuid4(),
        name="TestModel",
        llamacpp_version_hash="test_hash",
        gguf_filename="test.gguf",
        context_size=2048,
        ram_required_mb=1000
    )

    with patch.object(docker_manager, 'client') as mock_client:
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {
                    "8000/tcp": [{"HostPort": "12345"}]
                }
            }
        }
        mock_client.containers.run.return_value = mock_container
        
        # Mock get to raise NotFound
        import docker
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")

        # Mock HTTPConnection instance and response
        mock_conn_instance = MagicMock()
        mock_http_class.return_value = mock_conn_instance
        
        mock_response = MagicMock()
        mock_conn_instance.getresponse.return_value = mock_response
        
        container = docker_manager.start_model(model)

        assert container == mock_container
        mock_http_class.assert_called_once_with("127.0.0.1", 12345, timeout=0.5)
        mock_conn_instance.request.assert_called_once_with("GET", "/health")
        mock_response.read.assert_called_once()
        mock_conn_instance.close.assert_called_once()
        mock_sleep.assert_not_called()



