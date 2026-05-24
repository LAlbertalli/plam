import re
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.domain import ModelRegexRule, RegexChainEnum

class ProxyService:
    def apply_input_chain(self, text: str, model_id: UUID, db: Session) -> str:
        rules = db.query(ModelRegexRule).filter(
            ModelRegexRule.model_id == model_id,
            ModelRegexRule.chain == RegexChainEnum.input_chain,
            ModelRegexRule.is_active == True
        ).order_by(ModelRegexRule.order).all()
        
        modified_text = text
        for rule in rules:
            try:
                modified_text = re.sub(rule.pattern, rule.replacement, modified_text)
            except re.error:
                continue
        return modified_text

    def apply_output_chain(self, text: str, model_id: UUID, db: Session) -> str:
        rules = db.query(ModelRegexRule).filter(
            ModelRegexRule.model_id == model_id,
            ModelRegexRule.chain == RegexChainEnum.output_chain,
            ModelRegexRule.is_active == True
        ).order_by(ModelRegexRule.order).all()
        
        modified_text = text
        for rule in rules:
            try:
                modified_text = re.sub(rule.pattern, rule.replacement, modified_text)
            except re.error:
                continue
        return modified_text

proxy_service = ProxyService()

