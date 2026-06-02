from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.database import get_db
from app.models.domain import LLMModel
from app.models.schemas import LLMModelCreate, LLMModelUpdate, LLMModelResponse
from app.services.huggingface_downloader import downloader
from app.services.docker_manager import docker_manager
from app.core.config import MODELS_DIR
import docker
import os

router = APIRouter()

def _get_dynamic_status(model_id: UUID, current_status: str) -> str:
    if current_status in ["downloading", "error"]:
        return current_status
    try:
        if docker_manager.client:
            container = docker_manager.client.containers.get(f"plam-model-{model_id}")
            if container.status == "running":
                return "running"
    except docker.errors.NotFound:
        pass
    except Exception:
        pass
    return "stopped"

def _prepare_response(model: LLMModel) -> LLMModelResponse:
    resp = LLMModelResponse.model_validate(model)
    resp.status = _get_dynamic_status(model.id, model.status)
    if resp.gguf_filename:
        file_path = os.path.join(str(MODELS_DIR), resp.gguf_filename)
        resp.local_path = file_path if os.path.exists(file_path) else None
    resp.error_message = downloader.get_error(model.id)
    return resp

@router.get("/tasks")
def get_tasks():
    from app.models.domain import RecommendedTask
    return [task.value for task in RecommendedTask]

@router.get("", response_model=List[LLMModelResponse])
def get_models(db: Session = Depends(get_db)):
    models = db.query(LLMModel).all()
    return [_prepare_response(m) for m in models]

@router.get("/{model_id}", response_model=LLMModelResponse)
def get_model(model_id: UUID, db: Session = Depends(get_db)):
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _prepare_response(model)

@router.post("", response_model=LLMModelResponse)
def create_model(model_in: LLMModelCreate, db: Session = Depends(get_db)):
    db_model = LLMModel(**model_in.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return _prepare_response(db_model)

@router.put("/{model_id}", response_model=LLMModelResponse)
def update_model(model_id: UUID, model_in: LLMModelUpdate, db: Session = Depends(get_db)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    update_data = model_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_model, key, value)
        
    db.commit()
    db.refresh(db_model)
    return _prepare_response(db_model)

@router.post("/{model_id}/download", response_model=LLMModelResponse)
def download_model(model_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    background_tasks.add_task(downloader.download_model, model_id)
    
    db_model.status = "downloading"
    db.commit()
    db.refresh(db_model)
    return _prepare_response(db_model)

@router.post("/{model_id}/start", response_model=LLMModelResponse)
def start_model(model_id: UUID, db: Session = Depends(get_db)):
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    try:
        docker_manager.start_model(model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    db.refresh(model)
    return _prepare_response(model)

@router.post("/{model_id}/stop", response_model=LLMModelResponse)
def stop_model(model_id: UUID, db: Session = Depends(get_db)):
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    if docker_manager.is_model_in_use(model_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot stop model while it is currently in use by an active stream."
        )
        
    try:
        docker_manager.stop_model(model.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return _prepare_response(model)

@router.delete("/{model_id}")
def delete_model(model_id: UUID, db: Session = Depends(get_db)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    if db_model.gguf_filename:
        file_path = os.path.join(str(MODELS_DIR), db_model.gguf_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    db.delete(db_model)
    db.commit()
    return {"message": "Model deleted successfully"}
