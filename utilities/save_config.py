import os
import sys
import json
import argparse

# Dynamic path resolution to ensure app imports work when run as standalone script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.database import SessionLocal
from app.models.domain import LLMModel, Agent, ModelRegexRule

def load_existing_json(file_path: str) -> list:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Warning: Could not parse existing file {file_path}: {e}")
    return []

def save_config(agent_names: list, target_dir: str):
    print(f"Exporting agents {agent_names} to {target_dir}...")
    os.makedirs(target_dir, exist_ok=True)
    
    db = SessionLocal()
    try:
        # Load existing files to avoid losing other configurations
        models_file = os.path.join(target_dir, "models.json")
        agents_file = os.path.join(target_dir, "agents.json")
        rules_file = os.path.join(target_dir, "regex_rules.json")
        
        existing_models = load_existing_json(models_file)
        existing_agents = load_existing_json(agents_file)
        existing_rules = load_existing_json(rules_file)
        
        # Mappings of existing items by unique identifier to prevent duplicates
        models_map = {m["name"]: m for m in existing_models}
        agents_map = {a["name"]: a for a in existing_agents}
        # Unique identifier for rules: (model_name, chain, order)
        rules_map = {(r["model_name"], r["chain"], r["order"]): r for r in existing_rules}
        
        exported_agents_count = 0
        exported_models_count = 0
        exported_rules_count = 0
        
        for name in agent_names:
            agent = db.query(Agent).filter(Agent.name == name).first()
            if not agent:
                print(f"Warning: Agent '{name}' not found in database. Skipping.")
                continue
            
            # Fetch model details
            model = db.query(LLMModel).filter(LLMModel.id == agent.model_id).first()
            if not model:
                print(f"Warning: Model for agent '{name}' not found. Skipping.")
                continue
            
            # Add/Update model
            model_data = {
                "name": model.name,
                "hf_repo_id": model.hf_repo_id,
                "gguf_filename": model.gguf_filename,
                "ram_required_mb": model.ram_required_mb,
                "context_size": model.context_size,
                "llamacpp_args": model.llamacpp_args,
                "parameter_count": model.parameter_count,
                "quantization": model.quantization,
                "recommended_tasks": model.recommended_tasks,
                "llamacpp_version_hash": model.llamacpp_version_hash
            }
            if model.name not in models_map:
                exported_models_count += 1
            models_map[model.name] = model_data
            
            # Add/Update agent
            agent_data = {
                "name": agent.name,
                "description": agent.description,
                "model_name": model.name,
                "system_prompt": agent.system_prompt,
                "is_orchestrator": agent.is_orchestrator,
                "is_abstract": agent.is_abstract
            }
            if agent.name not in agents_map:
                exported_agents_count += 1
            agents_map[agent.name] = agent_data
            
            # Fetch and Add/Update model regex rules
            rules = db.query(ModelRegexRule).filter(ModelRegexRule.model_id == model.id).all()
            for rule in rules:
                chain_val = rule.chain.value if hasattr(rule.chain, "value") else str(rule.chain)
                rule_data = {
                    "model_name": model.name,
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "replacement": rule.replacement,
                    "chain": chain_val,
                    "order": rule.order,
                    "is_active": rule.is_active
                }
                rule_key = (model.name, chain_val, rule.order)
                if rule_key not in rules_map:
                    exported_rules_count += 1
                rules_map[rule_key] = rule_data
                
        # Write back updated lists
        with open(models_file, "w") as f:
            json.dump(list(models_map.values()), f, indent=2)
        with open(agents_file, "w") as f:
            json.dump(list(agents_map.values()), f, indent=2)
        with open(rules_file, "w") as f:
            json.dump(list(rules_map.values()), f, indent=2)
            
        print(f"Successfully exported/updated in {target_dir}:")
        print(f"  - Agents: {exported_agents_count} new/updated (total: {len(agents_map)})")
        print(f"  - Models: {exported_models_count} new/updated (total: {len(models_map)})")
        print(f"  - Regex Rules: {exported_rules_count} new/updated (total: {len(rules_map)})")
        
    except Exception as e:
        print(f"Error exporting configurations: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export PLAM Database configurations to JSON files.")
    parser.add_argument("--agents", nargs="+", required=True, help="List of agent names to export.")
    parser.add_argument("--config-dir", default="default-config", help="Target directory to save configurations. Default: default-config.")
    args = parser.parse_args()
    
    save_config(args.agents, args.config_dir)
