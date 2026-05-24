import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.domain import LLMModel, Agent, Package, AgentPackage, Skill, MCPTool
from app.services.agent_service import agent_service
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clear tables after each test to ensure isolation
        db.query(Skill).delete()
        db.query(MCPTool).delete()
        db.query(AgentPackage).delete()
        db.query(Package).delete()
        db.query(Agent).delete()
        db.query(LLMModel).delete()
        db.commit()
        db.close()

def test_agent_service_system_prompt_injection(db_session: Session):
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

    agent = Agent(
        id=uuid4(),
        name="TestAgent",
        model_id=model.id,
        system_prompt="You are a helpful assistant."
    )
    db_session.add(agent)
    db_session.commit()

    package = Package(id=uuid4(), name="TestPackage", description="A package")
    db_session.add(package)
    db_session.commit()

    link = AgentPackage(agent_id=agent.id, package_id=package.id)
    db_session.add(link)

    skill = Skill(
        id=uuid4(),
        package_id=package.id,
        name="test_skill",
        description="Does a test skill",
        front_matter={}
    )
    tool = MCPTool(
        id=uuid4(),
        package_id=package.id,
        name="test_tool",
        description="Does a test tool",
        mcp_schema={}
    )
    db_session.add(skill)
    db_session.add(tool)
    db_session.commit()

    system_prompt = agent_service.build_system_prompt(agent.id, db_session)
    
    assert "You are a helpful assistant." in system_prompt
    assert "test_skill" in system_prompt
    assert "test_tool" in system_prompt

def test_agent_service_agent_not_found(db_session: Session):
    prompt = agent_service.build_system_prompt(uuid4(), db_session)
    assert prompt == ""

def test_agent_service_agent_no_packages(db_session: Session):
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

    agent = Agent(
        id=uuid4(),
        name="TestAgent",
        model_id=model.id,
        system_prompt="You are a helpful assistant."
    )
    db_session.add(agent)
    db_session.commit()

    prompt = agent_service.build_system_prompt(agent.id, db_session)
    assert prompt == "You are a helpful assistant."
