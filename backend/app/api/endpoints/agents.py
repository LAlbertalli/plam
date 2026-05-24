from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.db.database import get_db
from app.models.domain import Agent
from app.models.schemas import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()

@router.get("", response_model=List[AgentResponse])
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()

@router.get("/{id}", response_model=AgentResponse)
def get_agent(id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("", response_model=AgentResponse, status_code=210) # 210 for created
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(Agent.name == agent_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent name already exists")
    
    agent = Agent(**agent_in.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

@router.put("/{id}", response_model=AgentResponse)
def update_agent(id: UUID, agent_in: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    update_data = agent_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
        
    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{id}")
def delete_agent(id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    db.delete(agent)
    db.commit()
    return {"status": "ok", "message": "Agent deleted"}
