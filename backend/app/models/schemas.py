from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.domain import ModelStatus, RecommendedTask

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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
