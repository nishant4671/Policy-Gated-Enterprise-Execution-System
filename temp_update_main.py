import sys
with open('agent/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def resume(' not in content:
    resume_func = '''
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
'''
    content += "\n" + resume_func
    
    with open('agent/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
