import pytest
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.domain import LLMModel, Agent, ModelRegexRule, RegexChainEnum
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clean up tables after each test to ensure isolation
        db.query(ModelRegexRule).delete()
        db.query(Agent).delete()
        db.query(LLMModel).delete()
        db.commit()
        db.close()

# --- Part 1: Model API Endpoints & Branch Coverage ---

def test_models_api_not_found(client):
    invalid_id = str(uuid4())
    
    # 404 for download
    res = client.post(f"/api/v1/models/{invalid_id}/download")
    assert res.status_code == 404
    assert res.json()["detail"] == "Model not found"
    
    # 404 for start
    res = client.post(f"/api/v1/models/{invalid_id}/start")
    assert res.status_code == 404
    assert res.json()["detail"] == "Model not found"
    
    # 404 for stop
    res = client.post(f"/api/v1/models/{invalid_id}/stop")
    assert res.status_code == 404
    assert res.json()["detail"] == "Model not found"
    
    # 404 for delete
    res = client.delete(f"/api/v1/models/{invalid_id}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Model not found"

@patch("app.api.endpoints.models.docker_manager.start_model")
def test_start_model_errors(mock_start, client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Test startup failure
    mock_start.side_effect = Exception("Docker launch failed")
    res = client.post(f"/api/v1/models/{model.id}/start")
    assert res.status_code == 500
    assert "Docker launch failed" in res.json()["detail"]

@patch("app.api.endpoints.models.docker_manager.is_model_in_use")
@patch("app.api.endpoints.models.docker_manager.stop_model")
def test_stop_model_in_use_and_errors(mock_stop, mock_in_use, client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # 1. Model in use error
    mock_in_use.return_value = True
    res = client.post(f"/api/v1/models/{model.id}/stop")
    assert res.status_code == 400
    assert "Cannot stop model while it is currently in use" in res.json()["detail"]

    # 2. Stop execution failure
    mock_in_use.return_value = False
    mock_stop.side_effect = Exception("Docker stop failed")
    res = client.post(f"/api/v1/models/{model.id}/stop")
    assert res.status_code == 500
    assert "Docker stop failed" in res.json()["detail"]

@patch("app.api.endpoints.models.os.path.exists")
@patch("app.api.endpoints.models.os.remove")
def test_delete_model_with_existing_file(mock_remove, mock_exists, client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Simulate model file exists
    mock_exists.return_value = True
    res = client.delete(f"/api/v1/models/{model.id}")
    assert res.status_code == 200
    assert mock_remove.called

    # Simulate remove exception handle
    mock_remove.side_effect = Exception("Permission error")
    model_2 = LLMModel(
        id=uuid4(),
        name="TestModel2",
        hf_repo_id="test/repo2",
        gguf_filename="test2.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model_2)
    db_session.commit()
    
    res = client.delete(f"/api/v1/models/{model_2.id}")
    assert res.status_code == 200  # Should pass silently despite remove failing

# --- Part 2: Agents API Endpoints ---

def test_agents_api_lifecycle(client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="ModelForAgent",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    agent_data = {
        "name": "Super Agent",
        "description": "A very helpful agent",
        "model_id": str(model.id),
        "system_prompt": "Prompt",
        "is_orchestrator": False,
        "is_abstract": False
    }

    # 1. Create Agent (POST)
    res = client.post("/api/v1/agents", json=agent_data)
    assert res.status_code == 210
    agent_id = res.json()["id"]
    assert res.json()["name"] == "Super Agent"

    # 2. Create Duplicate Name (POST) -> 400
    res = client.post("/api/v1/agents", json=agent_data)
    assert res.status_code == 400
    assert "Agent name already exists" in res.json()["detail"]

    # 3. Get All Agents (GET)
    res = client.get("/api/v1/agents")
    assert res.status_code == 200
    names = [a["name"] for a in res.json()]
    assert "Super Agent" in names

    # 4. Get Agent by ID (GET)
    res = client.get(f"/api/v1/agents/{agent_id}")
    assert res.status_code == 200
    assert res.json()["description"] == "A very helpful agent"

    # 5. Get Agent 404 (GET)
    res = client.get(f"/api/v1/agents/{uuid4()}")
    assert res.status_code == 404

    # 6. Update Agent (PUT)
    res = client.put(f"/api/v1/agents/{agent_id}", json={"description": "Updated agent description"})
    assert res.status_code == 200
    assert res.json()["description"] == "Updated agent description"

    # 7. Update Agent 404 (PUT)
    res = client.put(f"/api/v1/agents/{uuid4()}", json={"description": "test"})
    assert res.status_code == 404

    # 8. Delete Agent (DELETE)
    res = client.delete(f"/api/v1/agents/{agent_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 9. Delete Agent 404 (DELETE)
    res = client.delete(f"/api/v1/agents/{uuid4()}")
    assert res.status_code == 404

# --- Part 3: Proxies API Endpoints ---

def test_proxies_api_lifecycle(client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="ModelForRules",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    rule_data = {
        "model_id": str(model.id),
        "name": "Redact Keys",
        "pattern": "api_key",
        "replacement": "REDACTED",
        "chain": "input_chain",
        "order": 1,
        "is_active": True
    }

    # 1. Create Rule (POST)
    res = client.post("/api/v1/proxies", json=rule_data)
    assert res.status_code == 201
    rule_id = res.json()["id"]
    assert res.json()["name"] == "Redact Keys"

    # 2. Create Conflict Rule -> 400
    res = client.post("/api/v1/proxies", json=rule_data)
    assert res.status_code == 400
    assert "A rule already exists" in res.json()["detail"]

    # 3. Get Rules (GET)
    res = client.get("/api/v1/proxies")
    assert res.status_code == 200
    assert len(res.json()) > 0

    # 4. Get Rules for specific model (GET)
    res = client.get(f"/api/v1/proxies?model_id={model.id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

    # 5. Get Rule by ID (GET)
    res = client.get(f"/api/v1/proxies/{rule_id}")
    assert res.status_code == 200
    assert res.json()["replacement"] == "REDACTED"

    # 6. Get Rule 404 (GET)
    res = client.get(f"/api/v1/proxies/{uuid4()}")
    assert res.status_code == 404

    # 7. Update Rule (PUT)
    res = client.put(f"/api/v1/proxies/{rule_id}", json={"replacement": "HIDDEN"})
    assert res.status_code == 200
    assert res.json()["replacement"] == "HIDDEN"

    # 8. Update Rule 404 (PUT)
    res = client.put(f"/api/v1/proxies/{uuid4()}", json={"replacement": "test"})
    assert res.status_code == 404

    # 9. Update Rule Conflict (PUT)
    # Let's create a second rule
    rule2_data = {
        "model_id": str(model.id),
        "name": "Second Rule",
        "pattern": "secret",
        "replacement": "HIDDEN2",
        "chain": "input_chain",
        "order": 2,
        "is_active": True
    }
    res2 = client.post("/api/v1/proxies", json=rule2_data)
    rule2_id = res2.json()["id"]

    # Conflict order update
    res = client.put(f"/api/v1/proxies/{rule2_id}", json={"order": 1})
    assert res.status_code == 400
    assert "A rule already exists" in res.json()["detail"]

    # 10. Delete Rule (DELETE)
    res = client.delete(f"/api/v1/proxies/{rule_id}")
    assert res.status_code == 200
    
    # 11. Delete Rule 404 (DELETE)
    res = client.delete(f"/api/v1/proxies/{uuid4()}")
    assert res.status_code == 404

def test_proxies_api_test_endpoint(client, db_session):
    model = LLMModel(
        id=uuid4(),
        name="ModelForTesting",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    rule = ModelRegexRule(
        model_id=model.id,
        name="TestRule",
        pattern="apple",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    rule_out = ModelRegexRule(
        model_id=model.id,
        name="TestRuleOut",
        pattern="orange",
        replacement="pear",
        chain=RegexChainEnum.output_chain,
        order=1
    )
    db_session.add(rule)
    db_session.add(rule_out)
    db_session.commit()

    # 1. Test input_chain
    payload = {
        "text": "I eat an apple",
        "model_id": str(model.id),
        "chain": "input_chain"
    }
    res = client.post("/api/v1/proxies/test", json=payload)
    assert res.status_code == 200
    assert res.json()["result"] == "I eat an banana"

    # 2. Test output_chain
    payload["text"] = "I eat an orange"
    payload["chain"] = "output_chain"
    res = client.post("/api/v1/proxies/test", json=payload)
    assert res.status_code == 200
    assert res.json()["result"] == "I eat an pear"

    # 3. Invalid chain
    payload["chain"] = "invalid_chain"
    res = client.post("/api/v1/proxies/test", json=payload)
    assert res.status_code == 400
