import sys
with open('agent/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add route_human_decision
if 'def route_human_decision' not in content:
    router = '''
def route_human_decision(state: AgentState) -> str:
    decision = state.get("human_decision", "approved").lower()
    if decision == "approved":
        return "execute_node"
    else:
        return "block_node"
'''
    content = content.replace('def build_graph(', router + '\ndef build_graph(')

# Add conditional edges for human_approval_node
if 'builder.add_conditional_edges("human_approval_node"' not in content:
    edge_code = '''    builder.add_conditional_edges("human_approval_node", route_human_decision, {
        "execute_node": "execute_node",
        "block_node": "block_node"
    })'''
    content = content.replace('memory = MemorySaver()', edge_code + '\n    memory = MemorySaver()')

# Switch to SqliteSaver
if 'SqliteSaver' not in content:
    content = content.replace('from langgraph.checkpoint.memory import MemorySaver', 'from langgraph.checkpoint.sqlite import SqliteSaver')
    content = content.replace('memory = MemorySaver()', 'memory = SqliteSaver.from_conn_string("agent/checkpoints.db")')

# Ensure interrupt_after
if 'interrupt_after' not in content:
    content = content.replace('return builder.compile(checkpointer=memory)', 'return builder.compile(checkpointer=memory, interrupt_after=["human_approval_node"])')

with open('agent/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)
