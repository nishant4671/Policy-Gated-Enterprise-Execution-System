import sys

with open('agent/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

router = '''
def route_human_decision(state: AgentState) -> str:
    decision = state.get("human_decision", "approved").lower()
    if decision == "approved":
        return "execute_node"
    else:
        return "block_node"

def build_graph(safe_mode: bool = True):
'''

content = content.replace('def build_graph(safe_mode: bool = True):', router)

old_compile = '''    memory = MemorySaver()
    return builder.compile(checkpointer=memory)'''

new_compile = '''    builder.add_conditional_edges("human_approval_node", route_human_decision, {
        "execute_node": "execute_node",
        "block_node": "block_node"
    })
    
    memory = SqliteSaver.from_conn_string("agent/checkpoints.db")
    return builder.compile(checkpointer=memory, interrupt_after=["human_approval_node"])'''

content = content.replace(old_compile, new_compile)
content = content.replace('from langgraph.checkpoint.memory import MemorySaver', 'from langgraph.checkpoint.memory import MemorySaver\nfrom langgraph.checkpoint.sqlite import SqliteSaver')

with open('agent/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)
