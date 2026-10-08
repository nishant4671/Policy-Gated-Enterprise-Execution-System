import sys, os
sys.path.append(os.getcwd())
from agent.main import run
import json
print(json.dumps(run("Buy a laptop", 101, safe_mode=True), indent=2))
