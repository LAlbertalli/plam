from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from enum import Enum
from app.db.database import Base

class ModelStatus(str, Enum):
    stopped = "stopped"
    running = "running"
    downloading = "downloading"
    error = "error"

class RecommendedTask(str, Enum):
    coding = "Coding"
    general = "General"
    summarization = "Summarization"

class RoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"

class LLMModel(Base):
    __tablename__ = "models"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    hf_repo_id = Column(String, nullable=False)
    gguf_filename = Column(String, nullable=False)
    local_path = Column(String, nullable=True)
    status = Column(SQLEnum(ModelStatus), nullable=False, default=ModelStatus.stopped)
    ram_required_mb = Column(Integer, nullable=False)
    context_size = Column(Integer, nullable=False)
    llamacpp_args = Column(JSONB, nullable=True)
    parameter_count = Column(String, nullable=True)
    quantization = Column(String, nullable=True)
    recommended_tasks = Column(JSONB, nullable=True) # Array of strings stored as JSONB
    llamacpp_version_hash = Column(String, nullable=True, default="ff52ee9")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class Agent(Base):
    __tablename__ = "agents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    system_prompt = Column(Text, nullable=False)
    is_orchestrator = Column(Boolean, nullable=False, default=False)
    parent_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    is_abstract = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class Package(Base):
    __tablename__ = "packages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

class AgentPackage(Base):
    __tablename__ = "agent_packages"
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), primary_key=True)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id"), primary_key=True)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id"), nullable=False)
    name = Column(String, unique=True, nullable=False)
    front_matter = Column(JSONB, nullable=False)
    description = Column(Text, nullable=False)

class MCPTool(Base):
    __tablename__ = "mcp_tools"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id"), nullable=False)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    mcp_schema = Column(JSONB, nullable=False)
    endpoint_url = Column(String, nullable=True)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class ShortTermMemory(Base):
    __tablename__ = "short_term_memory"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    sequence_id = Column(Integer, nullable=False)
    role = Column(SQLEnum(RoleEnum), nullable=False)
    content = Column(Text, nullable=True)
    thinking_trace = Column(Text, nullable=True)
    tool_calls = Column(JSONB, nullable=True)
    tool_outputs = Column(JSONB, nullable=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
