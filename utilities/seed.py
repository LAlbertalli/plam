import os
import sys
import json
import argparse

# Dynamic path resolution to ensure app imports work when run as standalone script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.database import SessionLocal
from app.models.domain import LLMModel, Agent, ModelRegexRule, RegexChainEnum

def seed_db(config_dir: str):
    print(f"Loading configuration from: {config_dir}")
    db = SessionLocal()
    try:
        # 1. Seed Models
        models_file = os.path.join(config_dir, "models.json")
        model_name_to_id = {}
        
        if os.path.exists(models_file):
            with open(models_file, "r") as f:
                models_data = json.load(f)
            
            for m_data in models_data:
                name = m_data.get("name")
                if not name:
                    continue
                
                # Check if model exists
                db_model = db.query(LLMModel).filter(LLMModel.name == name).first()
                
                # Prepare fields
                fields = {
                    "hf_repo_id": m_data.get("hf_repo_id"),
                    "gguf_filename": m_data.get("gguf_filename"),
                    "ram_required_mb": m_data.get("ram_required_mb"),
                    "context_size": m_data.get("context_size"),
                    "llamacpp_args": m_data.get("llamacpp_args"),
                    "parameter_count": m_data.get("parameter_count"),
                    "quantization": m_data.get("quantization"),
                    "recommended_tasks": m_data.get("recommended_tasks"),
                    "llamacpp_version_hash": m_data.get("llamacpp_version_hash")
                }
                
                if db_model:
                    print(f"Updating model: {name}")
                    for key, val in fields.items():
                        setattr(db_model, key, val)
                else:
                    print(f"Creating model: {name}")
                    db_model = LLMModel(name=name, **fields)
                    db.add(db_model)
                
                db.commit()
                db.refresh(db_model)
                model_name_to_id[name] = db_model.id
        else:
            print("No models.json file found in config directory, skipping model seeding.")
            # Populate model_name_to_id with existing models in DB for agents/rules resolution
            for m in db.query(LLMModel).all():
                model_name_to_id[m.name] = m.id

        # 2. Seed Agents
        agents_file = os.path.join(config_dir, "agents.json")
        if os.path.exists(agents_file):
            with open(agents_file, "r") as f:
                agents_data = json.load(f)
            
            for a_data in agents_data:
                name = a_data.get("name")
                if not name:
                    continue
                
                model_name = a_data.get("model_name")
                model_id = model_name_to_id.get(model_name)
                
                if not model_id:
                    # Try looking up in DB
                    db_model = db.query(LLMModel).filter(LLMModel.name == model_name).first()
                    if db_model:
                        model_id = db_model.id
                    else:
                        print(f"Warning: Model '{model_name}' not found for agent '{name}'. Skipping.")
                        continue
                
                db_agent = db.query(Agent).filter(Agent.name == name).first()
                
                fields = {
                    "description": a_data.get("description"),
                    "model_id": model_id,
                    "system_prompt": a_data.get("system_prompt"),
                    "is_orchestrator": a_data.get("is_orchestrator", False),
                    "is_abstract": a_data.get("is_abstract", False)
                }
                
                if db_agent:
                    print(f"Updating agent: {name}")
                    for key, val in fields.items():
                        setattr(db_agent, key, val)
                else:
                    print(f"Creating agent: {name}")
                    db_agent = Agent(name=name, **fields)
                    db.add(db_agent)
                
                db.commit()
        else:
            print("No agents.json file found in config directory, skipping agent seeding.")

        # 3. Seed Regex Rules
        rules_file = os.path.join(config_dir, "regex_rules.json")
        if os.path.exists(rules_file):
            with open(rules_file, "r") as f:
                rules_data = json.load(f)
            
            for r_data in rules_data:
                rule_name = r_data.get("name")
                model_name = r_data.get("model_name")
                chain_str = r_data.get("chain")
                order = r_data.get("order")
                
                if not rule_name or not model_name or not chain_str or order is None:
                    continue
                
                model_id = model_name_to_id.get(model_name)
                if not model_id:
                    db_model = db.query(LLMModel).filter(LLMModel.name == model_name).first()
                    if db_model:
                        model_id = db_model.id
                    else:
                        print(f"Warning: Model '{model_name}' not found for regex rule '{rule_name}'. Skipping.")
                        continue
                
                try:
                    chain = RegexChainEnum[chain_str]
                except KeyError:
                    print(f"Warning: Invalid regex chain type '{chain_str}' for rule '{rule_name}'. Skipping.")
                    continue
                
                # Check for uniqueness constraint: (model_id, chain, order)
                db_rule = db.query(ModelRegexRule).filter(
                    ModelRegexRule.model_id == model_id,
                    ModelRegexRule.chain == chain,
                    ModelRegexRule.order == order
                ).first()
                
                fields = {
                    "name": rule_name,
                    "pattern": r_data.get("pattern"),
                    "replacement": r_data.get("replacement"),
                    "is_active": r_data.get("is_active", True)
                }
                
                if db_rule:
                    print(f"Updating regex rule: '{rule_name}' for model {model_name} ({chain_str}, order {order})")
                    for key, val in fields.items():
                        setattr(db_rule, key, val)
                else:
                    print(f"Creating regex rule: '{rule_name}' for model {model_name} ({chain_str}, order {order})")
                    db_rule = ModelRegexRule(
                        model_id=model_id,
                        chain=chain,
                        order=order,
                        **fields
                    )
                    db.add(db_rule)
                
                db.commit()
        else:
            print("No regex_rules.json file found in config directory, skipping regex rules seeding.")
            
        print("Configuration seeding completed successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed PLAM Database from a configuration folder containing JSON files.")
    parser.add_argument("--config-dir", required=True, help="Path to the directory containing JSON config files.")
    args = parser.parse_args()
    
    if not os.path.isdir(args.config_dir):
        print(f"Error: Directory '{args.config_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    seed_db(args.config_dir)
