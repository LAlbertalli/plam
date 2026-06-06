from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.domain import ModelStatus, RecommendedTask, RegexChainEnum, RoleEnum

# LLMModel schemas
class LLMModelBase(BaseModel):
    name: str
    hf_repo_id: str
    gguf_filename: str
    ram_required_mb: int
    context_size: int
    llamacpp_args: Optional[Dict[str, Any]] = None
    parameter_count: Optional[str] = None
    quantization: Optional[str] = None
    recommended_tasks: Optional[List[RecommendedTask]] = None
    llamacpp_version_hash: Optional[str] = "ff52ee9"

class LLMModelCreate(LLMModelBase):
    pass

class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    hf_repo_id: Optional[str] = None
    gguf_filename: Optional[str] = None
    ram_required_mb: Optional[int] = None
    context_size: Optional[int] = None
    llamacpp_args: Optional[Dict[str, Any]] = None
    parameter_count: Optional[str] = None
    quantization: Optional[str] = None
    recommended_tasks: Optional[List[RecommendedTask]] = None
    llamacpp_version_hash: Optional[str] = None

class LLMModelResponse(LLMModelBase):
    id: UUID
    local_path: Optional[str] = None
    status: ModelStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

# Regex Rule schemas
class ModelRegexRuleBase(BaseModel):
    model_id: UUID
    name: str
    pattern: str
    replacement: str
    chain: RegexChainEnum
    order: int
    is_active: bool = True

class ModelRegexRuleCreate(ModelRegexRuleBase):
    pass

class ModelRegexRuleUpdate(BaseModel):
    name: Optional[str] = None
    pattern: Optional[str] = None
    replacement: Optional[str] = None
    chain: Optional[RegexChainEnum] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

class ModelRegexRuleResponse(ModelRegexRuleBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

# Agent schemas
class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_id: UUID
    system_prompt: str
    is_orchestrator: bool = False
    parent_agent_id: Optional[UUID] = None
    is_abstract: bool = False

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_id: Optional[UUID] = None
    system_prompt: Optional[str] = None
    is_orchestrator: Optional[bool] = None
    parent_agent_id: Optional[UUID] = None
    is_abstract: Optional[bool] = None

class AgentResponse(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Package schemas
class PackageBase(BaseModel):
    name: str
    description: Optional[str] = None

class PackageCreate(PackageBase):
    pass

class PackageResponse(PackageBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# MCPServer schemas
class MCPServerBase(BaseModel):
    name: str
    connection_type: str
    command: Optional[str] = None
    args: Optional[List[Any]] = None
    env_encrypted: Optional[Dict[str, str]] = None
    sse_url: Optional[str] = None
    sse_headers_encrypted: Optional[Dict[str, str]] = None
    tools_hash: Optional[str] = None
    is_active: bool = True

class MCPServerCreate(MCPServerBase):
    pass

class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    connection_type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[Any]] = None
    env_encrypted: Optional[Dict[str, str]] = None
    sse_url: Optional[str] = None
    sse_headers_encrypted: Optional[Dict[str, str]] = None
    tools_hash: Optional[str] = None
    is_active: Optional[bool] = None

class MCPServerResponse(MCPServerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# MCPOAuthToken schemas
class MCPOAuthTokenBase(BaseModel):
    mcp_server_id: UUID
    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[Any]] = None

class MCPOAuthTokenCreate(MCPOAuthTokenBase):
    pass

class MCPOAuthTokenResponse(MCPOAuthTokenBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Skill schemas
class SkillBase(BaseModel):
    package_id: UUID
    name: str
    front_matter: Dict[str, Any]
    description: str
    source_path: Optional[str] = None
    content_hash: Optional[str] = None
    is_inferred: bool = False

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# MCPTool schemas
class MCPToolBase(BaseModel):
    package_id: UUID
    name: str
    description: str
    mcp_schema: Dict[str, Any]
    endpoint_url: Optional[str] = None
    mcp_server_id: Optional[UUID] = None
    content_hash: Optional[str] = None
    is_active: bool = True

class MCPToolCreate(MCPToolBase):
    pass

class MCPToolResponse(MCPToolBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# Session schemas
class SessionBase(BaseModel):
    title: Optional[str] = None

class SessionCreate(SessionBase):
    pass

class SessionResponse(SessionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ShortTermMemory schemas
class ShortTermMemoryBase(BaseModel):
    session_id: UUID
    agent_id: Optional[UUID] = None
    sequence_id: int
    role: RoleEnum
    content: Optional[str] = None
    thinking_trace: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_outputs: Optional[List[Dict[str, Any]]] = None

class ShortTermMemoryCreate(ShortTermMemoryBase):
    pass

class ShortTermMemoryResponse(ShortTermMemoryBase):
    id: UUID
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
