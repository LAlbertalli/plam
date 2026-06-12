import pytest
import json
import httpx
from uuid import uuid4
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.domain import LLMModel, Agent, Session as ChatSession, ShortTermMemory, RoleEnum
from app.services.orchestrator_service import orchestrator_service
from app.services.docker_manager import docker_manager
from tests.conftest import TestingSessionLocal

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

# --- Helper Mock for HTTPX Stream Response ---

class MockAsyncStreamResponse:
    def __init__(self, lines, status_code=200):
        self.lines = lines
        self.status_code = status_code
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def aiter_lines(self):
        for line in self.lines:
            yield line

# --- Tests for _get_active_model_port ---

@pytest.mark.asyncio
async def test_get_active_model_port_running():
    model = LLMModel(id=uuid4(), name="TestModel")
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {
        "NetworkSettings": {
            "Ports": {
                "8000/tcp": [{"HostPort": "12345"}]
            }
        }
    }
    
    with patch("app.services.orchestrator_service.docker_manager.get_model_container", return_value=mock_container):
        port, downloading = await orchestrator_service._get_active_model_port(model)
        assert port == "12345"
        assert not downloading

@pytest.mark.asyncio
async def test_get_active_model_port_starts_container():
    model = LLMModel(id=uuid4(), name="TestModel")
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {
        "NetworkSettings": {
            "Ports": {
                "8000/tcp": [{"HostPort": "54321"}]
            }
        }
    }
    
    with patch("app.services.orchestrator_service.docker_manager.get_model_container") as mock_get, \
         patch("app.services.orchestrator_service.docker_manager.start_model", return_value=True):
        
        mock_get.side_effect = [None, mock_container]
        
        port, downloading = await orchestrator_service._get_active_model_port(model)
        assert port == "54321"
        assert not downloading

@pytest.mark.asyncio
async def test_get_active_model_port_downloading():
    model = LLMModel(id=uuid4(), name="TestModel")
    
    with patch("app.services.orchestrator_service.docker_manager.get_model_container", return_value=None), \
         patch("app.services.orchestrator_service.docker_manager.start_model", return_value="downloading"):
        
        port, downloading = await orchestrator_service._get_active_model_port(model)
        assert port is None
        assert downloading

@pytest.mark.asyncio
async def test_get_active_model_port_start_fails():
    model = LLMModel(id=uuid4(), name="TestModel")
    
    with patch("app.services.orchestrator_service.docker_manager.get_model_container", return_value=None), \
         patch("app.services.orchestrator_service.docker_manager.start_model", return_value=False):
        
        with pytest.raises(RuntimeError) as exc_info:
            await orchestrator_service._get_active_model_port(model)
        assert "Failed to start model container" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_active_model_port_no_port_bound():
    model = LLMModel(id=uuid4(), name="TestModel")
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {
        "NetworkSettings": {
            "Ports": {}
        }
    }
    
    with patch("app.services.orchestrator_service.docker_manager.get_model_container", return_value=mock_container):
        with pytest.raises(RuntimeError) as exc_info:
            await orchestrator_service._get_active_model_port(model)
        assert "Model server failed to bind port" in str(exc_info.value)

# --- Tests for active_model_context ---

@pytest.mark.asyncio
async def test_active_model_context():
    model = LLMModel(id=uuid4(), name="TestModel")
    
    with patch.object(docker_manager, "increment_active_stream") as mock_inc, \
         patch.object(docker_manager, "decrement_active_stream") as mock_dec, \
         patch.object(orchestrator_service, "_get_active_model_port", return_value=("12345", False)):
        
        async with orchestrator_service.active_model_context(model) as (port, downloading):
            assert port == "12345"
            assert not downloading
            
        mock_inc.assert_called_once_with(model.id)
        mock_dec.assert_called_once_with(model.id)

# --- Tests for _calculate_stream_diff ---

def test_calculate_stream_diff(db_session):
    model_id = uuid4()
    
    # 1. Standard text delta (accumulated has new content)
    sanitized, payload = orchestrator_service._calculate_stream_diff(
        accumulated_response="Hello world this is a test",
        last_sent_sanitized="",
        model_id=model_id,
        db=db_session,
        delay_chars=0,
        is_final=False
    )
    assert sanitized == "Hello world this is a test"
    data = json.loads(payload.replace("data: ", "").strip())
    assert data["index"] == 0
    assert data["text"] == "Hello world this is a test"

    # 2. Duplicate output (no new text to send)
    sanitized2, payload2 = orchestrator_service._calculate_stream_diff(
        accumulated_response="Hello world this is a test",
        last_sent_sanitized="Hello world this is a test",
        model_id=model_id,
        db=db_session,
        delay_chars=0,
        is_final=False
    )
    assert sanitized2 == "Hello world this is a test"
    assert payload2 is None

    # 3. Final flush
    sanitized3, payload3 = orchestrator_service._calculate_stream_diff(
        accumulated_response="Hello world this is a test payload",
        last_sent_sanitized="Hello world this is a test",
        model_id=model_id,
        db=db_session,
        delay_chars=0,
        is_final=True
    )
    assert sanitized3 == "Hello world this is a test payload"
    data3 = json.loads(payload3.replace("data: ", "").strip())
    assert data3["index"] == 26
    assert data3["text"] == " payload"

# --- Tests for _execute_llm_request ---

@pytest.mark.asyncio
async def test_execute_llm_request_non_stream_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "reasoning_content": "Internal logic",
                "content": "Resulting text"
            }
        }]
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        gen = orchestrator_service._execute_llm_request(
            url="http://localhost:8000/v1/chat/completions",
            payload={},
            model_id=uuid4(),
            db=MagicMock(),
            stream=False
        )
        results = [x async for x in gen]
        assert len(results) == 1
        assert results[0][0] == "<thought>Internal logic</thought>Resulting text"
        assert results[0][1] is None

@pytest.mark.asyncio
async def test_execute_llm_request_non_stream_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        gen = orchestrator_service._execute_llm_request(
            url="http://localhost:8000/v1/chat/completions",
            payload={},
            model_id=uuid4(),
            db=MagicMock(),
            stream=False
        )
        with pytest.raises(RuntimeError) as exc_info:
            [x async for x in gen]
        assert "LLM Server Error: 500" in str(exc_info.value)

@pytest.mark.asyncio
async def test_execute_llm_request_stream_success():
    lines = [
        'data: {"choices": [{"delta": {"reasoning_content": "Deep"}}]}',
        'data: {"choices": [{"delta": {"reasoning_content": " thoughts"}}]}',
        'data: {"choices": [{"delta": {"content": "Answer"}}]}',
        'data: [DONE]'
    ]
    mock_stream_response = MockAsyncStreamResponse(lines)
    
    with patch("httpx.AsyncClient.stream", return_value=mock_stream_response):
        gen = orchestrator_service._execute_llm_request(
            url="http://localhost:8000/v1/chat/completions",
            payload={},
            model_id=uuid4(),
            db=MagicMock(),
            stream=True
        )
        results = [x async for x in gen]
        assert len(results) > 0
        final_response = results[-1][0]
        assert "<thought>Deep thoughts</thought>Answer" in final_response

@pytest.mark.asyncio
async def test_execute_llm_request_stream_error():
    mock_stream_response = MockAsyncStreamResponse([], status_code=500)
    
    with patch("httpx.AsyncClient.stream", return_value=mock_stream_response):
        gen = orchestrator_service._execute_llm_request(
            url="http://localhost:8000/v1/chat/completions",
            payload={},
            model_id=uuid4(),
            db=MagicMock(),
            stream=True
        )
        with pytest.raises(RuntimeError) as exc_info:
            [x async for x in gen]
        assert "LLM Server Error: 500" in str(exc_info.value)

# --- Tests for run_chat_stream ---

@pytest.mark.asyncio
async def test_run_chat_stream_agent_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    gen = orchestrator_service.run_chat_stream(
        agent_id=uuid4(),
        session_id=uuid4(),
        user_message="Hello",
        db=mock_db
    )
    results = [x async for x in gen]
    assert len(results) == 1
    data = json.loads(results[0].replace("data: ", "").strip())
    assert data["error"] == "Agent not found"

@pytest.mark.asyncio
async def test_run_chat_stream_model_not_found():
    mock_db = MagicMock()
    mock_agent = Agent(id=uuid4(), model_id=uuid4(), system_prompt="Prompt")
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_agent, # for Agent
        None # for Model
    ]
    
    gen = orchestrator_service.run_chat_stream(
        agent_id=mock_agent.id,
        session_id=uuid4(),
        user_message="Hello",
        db=mock_db
    )
    results = [x async for x in gen]
    assert len(results) == 1
    data = json.loads(results[0].replace("data: ", "").strip())
    assert data["error"] == "Model not found"

@pytest.mark.asyncio
async def test_run_chat_stream_downloading():
    mock_db = MagicMock()
    model_id = uuid4()
    mock_agent = Agent(id=uuid4(), model_id=model_id, system_prompt="Prompt")
    mock_model = LLMModel(id=model_id, name="DownloadingModel")
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_agent, # for Agent
        mock_model # for Model
    ]

    with patch.object(orchestrator_service, "_get_active_model_port", return_value=(None, True)):
        gen = orchestrator_service.run_chat_stream(
            agent_id=mock_agent.id,
            session_id=uuid4(),
            user_message="Hello",
            db=mock_db
        )
        results = [x async for x in gen]
        assert len(results) == 1
        data = json.loads(results[0].replace("data: ", "").strip())
        assert data["status"] == "downloading"

@pytest.mark.asyncio
async def test_run_chat_stream_success():
    mock_db = MagicMock()
    model_id = uuid4()
    mock_agent = Agent(id=uuid4(), model_id=model_id, system_prompt="Prompt")
    mock_model = LLMModel(id=model_id, name="ActiveModel")
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_agent, # for Agent
        mock_model, # for Model
    ]
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    mock_port_context = MagicMock()
    mock_port_context.__aenter__.return_value = ("12345", False)
    
    lines = [
        'data: {"choices": [{"delta": {"content": "Hello world"}}]}',
        'data: [DONE]'
    ]
    mock_stream_response = MockAsyncStreamResponse(lines)

    with patch.object(orchestrator_service, "active_model_context", return_value=mock_port_context), \
         patch("httpx.AsyncClient.stream", return_value=mock_stream_response), \
         patch("app.services.orchestrator_service.agent_service.build_system_prompt", return_value="System prompt"):
        
        gen = orchestrator_service.run_chat_stream(
            agent_id=mock_agent.id,
            session_id=uuid4(),
            user_message="Hello!",
            db=mock_db
        )
        results = [x async for x in gen]
        assert len(results) > 0
        
        done_data = json.loads(results[-1].replace("data: ", "").strip())
        assert done_data["done"] is True
        assert done_data["content"] == "Hello world"

        assert mock_db.add.called
        assert mock_db.commit.called
