import sys
with open('agent/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# We will just rewrite the execute_node completely
execute_orig_pattern = r'def execute_node\(state: AgentState\) -> dict:.*?(?=def block_node)'
execute_new = '''def execute_node(state: AgentState) -> dict:
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

'''
content = re.sub(execute_orig_pattern, execute_new, content, flags=re.DOTALL)

# block_node wrap
block_orig_pattern = r'def block_node\(state: AgentState\) -> dict:.*?(?=def route_policy)'
block_new = '''def block_node(state: AgentState) -> dict:
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

'''
content = re.sub(block_orig_pattern, block_new, content, flags=re.DOTALL)

# policy_check_node wrap
policy_orig_pattern = r'def policy_check_node\(state: AgentState\) -> dict:.*?(?=def human_approval_node)'
policy_new = '''def policy_check_node(state: AgentState) -> dict:
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

'''
content = re.sub(policy_orig_pattern, policy_new, content, flags=re.DOTALL)

with open('agent/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)
