import yaml
import os

POLICY_FILE = os.path.join(os.path.dirname(__file__), "policy.yaml")

with open(POLICY_FILE, "r") as f:
    POLICY = yaml.safe_load(f)
RULES = POLICY.get("rules", [])

def check_policy(action: str, context: dict) -> dict:
    ctx = context.copy()
    ctx["action"] = action
    
    for rule in RULES:
        try:
            if eval(rule["condition"], {}, ctx):
                return {"verdict": rule["verdict"], "rule": rule["name"]}
        except Exception:
            return {"verdict": "BLOCK", "rule": "evaluation_error"}
            
    return {"verdict": "ALLOW", "rule": "default"}
