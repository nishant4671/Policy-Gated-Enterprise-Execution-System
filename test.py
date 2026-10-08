from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict):
    decision: str
    log: list

def n1(state): return {"log": ["n1"]}
def n2(state): return {"log": ["n2"]}
def n3(state): return {"log": ["n3"]}

def route(state):
    print("Evaluating route. decision:", state.get("decision"))
    if state.get("decision") == "approved": return "n2"
    elif state.get("decision") == "rejected": return "n3"
    else: return "n2" # If pending, route to n2 so we pause before it?

def merge_log(log1, log2): return log1 + log2

builder = StateGraph(State)
builder.add_node("n1", n1)
builder.add_node("n2", n2)
builder.add_node("n3", n3)
builder.add_edge(START, "n1")
builder.add_conditional_edges("n1", route)
app = builder.compile(checkpointer=MemorySaver(), interrupt_before=["n2", "n3"])

config = {"configurable": {"thread_id": "1"}}
res = app.invoke({"decision": "pending", "log": []}, config)
print("After first run next nodes:", app.get_state(config).next)

app.update_state(config, {"decision": "rejected"})
res = app.invoke(None, config)
print("After second run:", app.get_state(config).values)
