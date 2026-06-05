import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from app.models.domain import Session as ChatSession, Agent, LLMModel
from tests.conftest import TestingSessionLocal

@pytest.fixture
def mock_db_data():
    db = TestingSessionLocal()
    
    # 1. Create a model
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db.add(model)
    db.commit()
    
    # 2. Create an agent
    agent = Agent(
        id=uuid4(),
        name="TestAgent",
        model_id=model.id,
        system_prompt="System Prompt"
    )
    db.add(agent)
    db.commit()
    
    # 3. Create a session
    session = ChatSession(
        id=uuid4(),
        title="Original Title"
    )
    db.add(session)
    db.commit()
    
    yield {
        "agent_id": agent.id,
        "session_id": session.id
    }
    
    # Clean up
    db.delete(session)
    db.delete(agent)
    db.delete(model)
    db.commit()
    db.close()

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_streaming(mock_run_chat_stream, client, mock_db_data):
    # Setup mock async generator
    async def mock_generator(*args, **kwargs):
        yield "data: {\"index\": 0, \"text\": \"Hello\"}\n\n"
        yield "data: {\"index\": 5, \"text\": \" world\"}\n\n"
        yield "data: {\"done\": true, \"content\": \"Hello world\", \"thinking_trace\": \"Thinking...\"}\n\n"
        
    mock_run_chat_stream.return_value = mock_generator()
    
    session_id = mock_db_data["session_id"]
    agent_id = mock_db_data["agent_id"]
    
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={
            "agent_id": str(agent_id),
            "content": "Hi agent",
            "stream": True
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Verify generator was called with stream=True
    mock_run_chat_stream.assert_called_once()
    assert mock_run_chat_stream.call_args[1]["stream"] is True
    
    # Read stream chunks
    chunks = [chunk for chunk in response.iter_lines() if chunk.strip()]
    assert len(chunks) >= 3
    assert "Hello" in chunks[0]
    assert "world" in chunks[1]
    assert "done" in chunks[2]

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_non_streaming(mock_run_chat_stream, client, mock_db_data):
    # Setup mock async generator
    async def mock_generator(*args, **kwargs):
        yield "data: {\"done\": true, \"content\": \"Hello non-stream\", \"thinking_trace\": \"Thinking non-stream...\"}\n\n"
        
    mock_run_chat_stream.return_value = mock_generator()
    
    session_id = mock_db_data["session_id"]
    agent_id = mock_db_data["agent_id"]
    
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={
            "agent_id": str(agent_id),
            "content": "Hi agent",
            "stream": False
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Read stream chunks
    chunks = [chunk for chunk in response.iter_lines() if chunk.strip()]
    assert len(chunks) == 1
    assert "done" in chunks[0]
    
    # Verify generator was called with stream=False
    mock_run_chat_stream.assert_called_once()
    assert mock_run_chat_stream.call_args[1]["stream"] is False

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_non_streaming_error(mock_run_chat_stream, client, mock_db_data):
    # Setup mock async generator that yields an error
    async def mock_generator(*args, **kwargs):
        yield "data: {\"error\": \"Some mock error occurred\"}\n\n"
        
    mock_run_chat_stream.return_value = mock_generator()
    
    session_id = mock_db_data["session_id"]
    agent_id = mock_db_data["agent_id"]
    
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={
            "agent_id": str(agent_id),
            "content": "Hi agent",
            "stream": False
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    chunks = [chunk for chunk in response.iter_lines() if chunk.strip()]
    assert len(chunks) == 1
    assert "Some mock error occurred" in chunks[0]

def test_get_sessions(client, mock_db_data):
    response = client.get("/api/v1/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert any(s["id"] == str(mock_db_data["session_id"]) for s in data)

def test_get_session_by_id(client, mock_db_data):
    session_id = mock_db_data["session_id"]
    response = client.get(f"/api/v1/chat/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(session_id)

def test_get_session_by_id_not_found(client):
    response = client.get(f"/api/v1/chat/sessions/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

def test_get_session_history(client, mock_db_data):
    session_id = mock_db_data["session_id"]
    response = client.get(f"/api/v1/chat/sessions/{session_id}/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_session_history_not_found(client):
    response = client.get(f"/api/v1/chat/sessions/{uuid4()}/history")
    assert response.status_code == 404

def test_create_session(client):
    response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Created Session"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Created Session"
    assert "id" in data

def test_delete_session(client, mock_db_data):
    session_id = mock_db_data["session_id"]
    response = client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
    # Try to get it again, should fail
    response_get = client.get(f"/api/v1/chat/sessions/{session_id}")
    assert response_get.status_code == 404

def test_delete_session_not_found(client):
    response = client.delete(f"/api/v1/chat/sessions/{uuid4()}")
    assert response.status_code == 404

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_session_not_found(mock_run_chat_stream, client, mock_db_data):
    response = client.post(
        f"/api/v1/chat/sessions/{uuid4()}/message",
        json={
            "agent_id": str(mock_db_data["agent_id"]),
            "content": "Hi",
            "stream": False
        }
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_downloading_error(mock_run_chat_stream, client, mock_db_data):
    async def mock_generator(*args, **kwargs):
        yield "data: {\"status\": \"downloading\", \"message\": \"Downloading...\"}\n\n"
        
    mock_run_chat_stream.return_value = mock_generator()
    
    session_id = mock_db_data["session_id"]
    agent_id = mock_db_data["agent_id"]
    
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={
            "agent_id": str(agent_id),
            "content": "Hi agent",
            "stream": False
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    chunks = [chunk for chunk in response.iter_lines() if chunk.strip()]
    assert len(chunks) == 1
    assert "downloading" in chunks[0]

@patch('app.api.endpoints.chat.orchestrator_service.run_chat_stream')
def test_send_message_json_decode_error(mock_run_chat_stream, client, mock_db_data):
    async def mock_generator(*args, **kwargs):
        yield "data: invalid-json-string\n\n"
        yield "data: {\"done\": true, \"content\": \"Valid JSON\", \"thinking_trace\": \"Trace\"}\n\n"
        
    mock_run_chat_stream.return_value = mock_generator()
    
    session_id = mock_db_data["session_id"]
    agent_id = mock_db_data["agent_id"]
    
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={
            "agent_id": str(agent_id),
            "content": "Hi agent",
            "stream": False
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    chunks = [chunk for chunk in response.iter_lines() if chunk.strip()]
    assert len(chunks) == 2
    assert "invalid-json-string" in chunks[0]
    assert "Valid JSON" in chunks[1]
