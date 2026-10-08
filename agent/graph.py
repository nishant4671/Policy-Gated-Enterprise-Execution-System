import os
import json
import uuid
import time
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from agent.state import AgentState
from agent.tools import get_employee, check_budget, list_products, place_order, send_email, write_audit
from policy_engine.engine import check_policy

load_dotenv()

def _make_llm():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("[LLM] Using Groq (openai/gpt-oss-120b)", flush=True)
        return ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=groq_key,
            max_retries=1,
        )
    print("[LLM] Falling back to Gemini", flush=True)
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

llm = _make_llm()

def _safe_llm_invoke(llm_instance, messages, max_retries=2, base_wait=10):
    last_err = None
    for attempt in range(max_retries):
        try:
            return llm_instance.invoke(messages)
        except Exception as e:
            last_err = e
            err = str(e).lower()
            if any(k in err for k in ["rate", "429", "quota", "resource_exhausted", "timeout"]):
                wait = base_wait * (2 ** attempt)
                print(f"[RETRY] attempt {attempt+1}/{max_retries} after {wait}s: {e}", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"LLM invoke failed after {max_retries} retries: {last_err}")

def plan_node(state: AgentState) -> dict:
    req = state["messages"][-1]
    req_content = str(req.content if hasattr(req, "content") else req).lower()
    keywords = ["laptop", "monitor", "keyboard", "mouse", "equipment", "cheapbook"]
    if sum(1 for kw in keywords if kw in req_content) < 1:
        return {"status": "blocked", "final_result": "Request unclear. Please specify product."}
    
    if any(kw in req_content for kw in ["ignore", "bypass", "override", "system prompt"]):
        return {"status": "blocked", "final_result": "Policy violation: Prompt injection detected"}

    req = state["messages"][-1]
    emp_id = state["employee_id"]
    
    prompt = f"User request: '{req}'. Employee ID: {emp_id}. Map the requested product to one of these valid categories: 'laptop', 'monitor', 'keyboard', 'mouse'. Return JSON exactly: {{\"product_category\": \"<string>\", \"preferred_price_max\": <number>}}"
    
    resp = _safe_llm_invoke(llm, [HumanMessage(content=prompt)])
    content = resp.content.strip()
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        data = json.loads(content)
    except Exception:
        return {"status": "blocked", "final_result": "Could not understand request"}
    if "product_category" not in data or not data["product_category"]:
        return {"status": "blocked", "final_result": "Could not understand request"}
        
    return {
        "product_info": data,
        "status": "planning"
    }

def fetch_info_node(state: AgentState) -> dict:
    try:
        emp = get_employee(state["employee_id"])
    except Exception:
        emp = {}
    if not emp or emp.get("error"):
        return {"status": "blocked", "final_result": "Employee not found", "employee_info": {}}
    dept = emp.get("department", "Unknown")
    
    budget = check_budget(dept)
    rem_budget = budget.get("remaining", 0.0)
    
    cat = state.get("product_info", {}).get("product_category", "laptop")
    prods = list_products(cat)
    
    new_messages = state.get("messages", []) + [str(prods)]
    
    return {
        "employee_info": emp,
        "department": dept,
        "remaining_budget": rem_budget,
        "products": prods,
        "messages": new_messages
    }

def select_product_node(state: AgentState) -> dict:
    products = state.get("products", [])
    rem_budget = state.get("remaining_budget", 0.0)
    req = str(state.get("messages", [""])[0]).lower()
    
    cat = state.get("product_info", {}).get("product_category", "laptop")
    approved_products = [p for p in products if p.get("vendor_approved") == 1 and p.get("price", float('inf')) <= rem_budget and p.get("category", "").lower() == cat.lower()]
    
    if not approved_products:
        return {
            "status": "blocked",
            "final_result": f"No products available in category {cat}",
            "cost": 0.0,
            "vendor_approved": False
        }
        
    import re
    premium_keywords = ["premium", "high-end", "high end", "best", "top"]
    is_premium = any(re.search(rf"\b{re.escape(kw)}\b", req) for kw in premium_keywords)
    
    if is_premium:
        selected = max(approved_products, key=lambda p: p["price"])
    else:
        selected = min(approved_products, key=lambda p: p["price"])
    
    return {
        "product_id": selected["id"],
        "cost": selected["price"],
        "vendor_approved": True,
        "product_info": selected
    }

def policy_check_node(state: AgentState) -> dict:
    try:
        emp = state.get("employee_info", {})
        context = {
            "cost": state.get("cost", 0.0),
            "vendor_approved": state.get("vendor_approved", False),
            "employee_role": emp.get("role", "Unknown"),
            "remaining_budget": state.get("remaining_budget", 0.0)
        }
        
        res = check_policy("purchase", context)
        return {
            "policy_verdict": res["verdict"],
            "policy_rule": res["rule"]
        }
    except Exception as e:
        write_audit(trace_id=state.get("trace_id",""), actor="agent", action="policy_error", result="FAILED", tool_called="none", arguments="{}", policy_verdict="ERROR", policy_rule="none")
        return {"status": "error", "final_result": str(e), "policy_verdict": "BLOCK", "policy_rule": "error"}

def human_approval_node(state: AgentState) -> dict:
    import json
    product_info = state.get("product_info") or {}
    approval_context = {
        "product_id": state.get("product_id"),
        "product_name": product_info.get("name"),
        "product_price": product_info.get("price"),
        "cost": state.get("cost"),
        "employee_id": state.get("employee_id"),
        "department": state.get("department"),
        "rule_triggered": state.get("policy_rule"),
    }
    write_audit(
        trace_id=state.get("trace_id", ""),
        actor="agent",
        action="purchase",
        tool_called="human_approval",
        arguments=json.dumps(approval_context),
        policy_verdict="REQUIRE_HUMAN_APPROVAL",
        policy_rule=state.get("policy_rule", ""),
        result="PENDING"
    )
    return {"status": "awaiting_approval"}

def execute_node(state: AgentState) -> dict:
    try:
        prod_id = state.get("product_id")
        emp_id = state.get("employee_id")
        trace_id = state.get("trace_id", "")
        
        place_order(prod_id, emp_id, trace_id)
        send_email("admin@company.com", "Order Placed", f"Ordered product {prod_id}", trace_id)
        
        return {
            "status": "done",
            "final_result": "Order placed"
        }
    except Exception as e:
        write_audit(trace_id=state.get("trace_id",""), actor="agent", action="execute_error", result="FAILED", tool_called="none", arguments="{}", policy_verdict="ERROR", policy_rule="none")
        return {"status": "error", "final_result": str(e)}

def block_node(state: AgentState) -> dict:
    try:
        final = state.get("final_result")
        rule = state.get("policy_rule", "unknown")
        if not final or final == "No approved product within budget":
            if rule != "default" and rule != "Unapproved Vendor":
                final = rule
                
        write_audit(
            trace_id=state.get("trace_id", ""),
            actor="agent",
            action="purchase",
            tool_called="none",
            arguments="{}",
            policy_verdict="BLOCK",
            policy_rule=rule,
            result="BLOCKED"
        )
        return {
            "status": "blocked",
            "final_result": final or rule
        }
    except Exception as e:
        write_audit(trace_id=state.get("trace_id",""), actor="agent", action="block_error", result="FAILED", tool_called="none", arguments="{}", policy_verdict="ERROR", policy_rule="none")
        return {"status": "error", "final_result": str(e)}

def route_policy(state: AgentState) -> str:
    v = state.get("policy_verdict")
    if v == "ALLOW":
        return "execute_node"
    elif v == "REQUIRE_HUMAN_APPROVAL":
        return "human_approval_node"
    else:
        return "block_node"


def route_human_decision(state: AgentState) -> str:
    decision = state.get("human_decision")
    print(f"[DEBUG] route_human_decision: decision={decision}")
    if not decision:
        decision = "approved"
    if decision.lower() == "approved":
        return "execute_node"
    else:
        return "block_node"

def route_plan(state: AgentState) -> str:
    if state.get("status") == "blocked":
        return "block_node"
    return "fetch_info_node"

def route_fetch(state: AgentState) -> str:
    if state.get("status") == "blocked":
        return "block_node"
    return "select_product_node"

def build_graph(safe_mode: bool = True):

    builder = StateGraph(AgentState)
    
    def custom_policy_check(state: AgentState) -> dict:
        if not safe_mode:
            return {"policy_verdict": "ALLOW", "policy_rule": "naive_bypass"}
        return policy_check_node(state)
    
    builder.add_node("plan_node", plan_node)
    builder.add_node("fetch_info_node", fetch_info_node)
    builder.add_node("select_product_node", select_product_node)
    builder.add_node("policy_check_node", custom_policy_check)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("execute_node", execute_node)
    builder.add_node("block_node", block_node)
    
    builder.add_edge(START, "plan_node")
    builder.add_conditional_edges("plan_node", route_plan, {"block_node": "block_node", "fetch_info_node": "fetch_info_node"})
    builder.add_conditional_edges("fetch_info_node", route_fetch, {"block_node": "block_node", "select_product_node": "select_product_node"})
    builder.add_edge("select_product_node", "policy_check_node")
    
    builder.add_conditional_edges("policy_check_node", route_policy, {
        "execute_node": "execute_node",
        "block_node": "block_node",
        "human_approval_node": "human_approval_node"
    })
    
    builder.add_conditional_edges("human_approval_node", route_human_decision, {
        "execute_node": "execute_node",
        "block_node": "block_node"
    })
    
    import sqlite3
    conn = sqlite3.connect("agent/checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    return builder.compile(checkpointer=memory, interrupt_after=["human_approval_node"])

if __name__ == "__main__":
    app = build_graph()
