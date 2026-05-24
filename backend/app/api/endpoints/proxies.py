from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.db.database import get_db
from app.models.domain import ModelRegexRule
from app.models.schemas import ModelRegexRuleCreate, ModelRegexRuleUpdate, ModelRegexRuleResponse
from app.services.proxy_service import proxy_service
from pydantic import BaseModel

router = APIRouter()

class ProxyTestRequest(BaseModel):
    text: str
    model_id: UUID
    chain: str # "input_chain" or "output_chain"

@router.get("", response_model=List[ModelRegexRuleResponse])
def get_rules(
    model_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ModelRegexRule)
    if model_id:
        query = query.filter(ModelRegexRule.model_id == model_id)
    return query.order_by(ModelRegexRule.chain, ModelRegexRule.order).all()

@router.get("/{id}", response_model=ModelRegexRuleResponse)
def get_rule(id: UUID, db: Session = Depends(get_db)):
    rule = db.query(ModelRegexRule).filter(ModelRegexRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.post("", response_model=ModelRegexRuleResponse, status_code=201)
def create_rule(rule_in: ModelRegexRuleCreate, db: Session = Depends(get_db)):
    # Check for unique constraint (model_id, chain, order)
    existing = db.query(ModelRegexRule).filter(
        ModelRegexRule.model_id == rule_in.model_id,
        ModelRegexRule.chain == rule_in.chain,
        ModelRegexRule.order == rule_in.order
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"A rule already exists for this model in {rule_in.chain} at order {rule_in.order}"
        )
        
    rule = ModelRegexRule(**rule_in.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.put("/{id}", response_model=ModelRegexRuleResponse)
def update_rule(id: UUID, rule_in: ModelRegexRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(ModelRegexRule).filter(ModelRegexRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    update_data = rule_in.model_dump(exclude_unset=True)
    
    # Check unique constraint if model_id, chain, or order are being changed
    new_model_id = update_data.get("model_id", rule.model_id)
    new_chain = update_data.get("chain", rule.chain)
    new_order = update_data.get("order", rule.order)
    
    if (new_model_id != rule.model_id or new_chain != rule.chain or new_order != rule.order):
        existing = db.query(ModelRegexRule).filter(
            ModelRegexRule.model_id == new_model_id,
            ModelRegexRule.chain == new_chain,
            ModelRegexRule.order == new_order,
            ModelRegexRule.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"A rule already exists for this model in {new_chain} at order {new_order}"
            )
            
    for field, value in update_data.items():
        setattr(rule, field, value)
        
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/{id}")
def delete_rule(id: UUID, db: Session = Depends(get_db)):
    rule = db.query(ModelRegexRule).filter(ModelRegexRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    db.delete(rule)
    db.commit()
    return {"status": "ok", "message": "Rule deleted"}

@router.post("/test")
def test_regex_chain(req: ProxyTestRequest, db: Session = Depends(get_db)):
    if req.chain == "input_chain":
        result = proxy_service.apply_input_chain(req.text, req.model_id, db)
    elif req.chain == "output_chain":
        result = proxy_service.apply_output_chain(req.text, req.model_id, db)
    else:
        raise HTTPException(status_code=400, detail="Invalid chain type. Must be 'input_chain' or 'output_chain'")
    return {"original": req.text, "result": result}
