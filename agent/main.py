import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sys
import uuid
from agent.graph import build_graph

def run(request: str, employee_id: int, safe_mode: bool = True):
    trace_id = str(uuid.uuid4())
    app = build_graph(safe_mode=safe_mode)
    initial_state = {
        "messages": [request],
        "employee_id": employee_id,
        "trace_id": trace_id,
        "status": "starting",
        "human_decision": "pending",
    }
    config = {"configurable": {"thread_id": trace_id}}
    result = app.invoke(initial_state, config=config)
    print("TRACE_ID:", trace_id)
    print("STATUS:", result.get("status"))
    print("VERDICT:", result.get("policy_verdict"))
    print("RULE:", result.get("policy_rule"))
    print("FINAL:", result.get("final_result"))
    return result

if __name__ == "__main__":
    safe_mode = "--naive" not in sys.argv
    args = [a for a in sys.argv[1:] if a != "--naive"]
    request = args[0] if len(args) > 0 else "Buy a laptop"
    employee_id = int(args[1]) if len(args) > 1 else 101
    run(request, employee_id, safe_mode=safe_mode)


def resume(trace_id: str):
    """Resume a paused workflow from its checkpoint."""
    from agent.graph import build_graph
    app = build_graph()
    config = {"configurable": {"thread_id": trace_id}}
    # Update state so the conditional edge routes correctly
    app.update_state(config, {"human_decision": "approved"})
    # LangGraph will load the checkpoint and continue from human_approval_node
    result = app.invoke(None, config=config)
    print("RESUMED TRACE:", trace_id)
    print("STATUS:", result.get("status"))
    print("FINAL:", result.get("final_result"))
    return result
