from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import json
from app.db.database import get_db
from app.models.domain import Session as ChatSession, ShortTermMemory
from app.models.schemas import SessionCreate, SessionResponse, ShortTermMemoryResponse
from app.services.orchestrator_service import orchestrator_service
from pydantic import BaseModel

router = APIRouter()

class MessageRequest(BaseModel):
    agent_id: UUID
    content: str
    stream: bool = True

@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(db: Session = Depends(get_db)):
    return db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()

@router.get("/sessions/{id}", response_model=SessionResponse)
def get_session(id: UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/sessions/{id}/history", response_model=List[ShortTermMemoryResponse])
def get_session_history(id: UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db.query(ShortTermMemory).filter(
        ShortTermMemory.session_id == id
    ).order_by(ShortTermMemory.sequence_id.asc()).all()

@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(session_in: SessionCreate, db: Session = Depends(get_db)):
    session = ChatSession(**session_in.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.delete("/sessions/{id}")
def delete_session(id: UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Delete associated memories
    db.query(ShortTermMemory).filter(ShortTermMemory.session_id == id).delete()
    db.delete(session)
    db.commit()
    return {"status": "ok", "message": "Session and history deleted"}

@router.post("/sessions/{session_id}/message")
async def send_message_stream(
    session_id: UUID,
    req: MessageRequest,
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Touch session to update updated_at timestamp
    session.title = req.content[:30] + "..." if not session.title else session.title
    db.commit()
    
    # We yield SSE formatted chunks
    generator = orchestrator_service.run_chat_stream(
        agent_id=req.agent_id,
        session_id=session_id,
        user_message=req.content,
        db=db,
        stream=req.stream
    )
    
    return StreamingResponse(generator, media_type="text/event-stream")
