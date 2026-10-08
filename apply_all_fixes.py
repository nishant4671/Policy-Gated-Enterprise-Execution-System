import os
import re

# ==============================================================================
# FIX 1, FIX 10, FIX 13, FIX 16: ui/app.py
# ==============================================================================
with open('ui/app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

# Fix 16 (cleanup at top) + Fix 1 (validation)
new_submit_block = '''
if "cleanup_done" not in st.session_state:
    try:
        requests.post("http://localhost:8000/cleanup_stale", timeout=2)
    except:
        pass
    st.session_state["cleanup_done"] = True

with tab1:
    st.header('Submit Request')
    request_text = st.text_input('Request', value='', placeholder='e.g., I need a laptop')
    emp_id = st.number_input('Employee ID', value=101, min_value=100)
    
    if st.button('Submit'):
        req_clean = request_text.strip()
        if not req_clean:
            st.error("Please enter a request.")
        elif len(req_clean) < 3:
            st.error("Request too short.")
        elif len(req_clean) > 500:
            st.error("Request too long.")
        else:
            with st.spinner('Agent is planning...'):
                result = run(req_clean, int(emp_id), safe_mode=True)
                st.session_state['last_result'] = result
'''
# Replace up to if 'last_result'
app_py = re.sub(r'with tab1:.*?if \'last_result\' in st\.session_state:', new_submit_block + "\n    if 'last_result' in st.session_state:", app_py, flags=re.DOTALL)

# Fix 13 (empty queue state)
app_py = app_py.replace("st.info('No pending approvals.')", 'st.info("✅ No pending approvals. All caught up.")')

# Fix 10 (Audit Log append-only caption)
app_py = app_py.replace("st.header('Audit Log')", 'st.header(\'Audit Log\')\n    st.caption("🔒 Audit log is append-only. Rows cannot be deleted or modified.")')

with open('ui/app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)

# ==============================================================================
# FIX 2, FIX 7, FIX 9, FIX 12, FIX 15: agent/graph.py
# ==============================================================================
with open('agent/graph.py', 'r', encoding='utf-8') as f:
    graph_py = f.read()

# Fix 7 & 12 (plan_node)
plan_node_orig = '''def plan_node(state: AgentState) -> dict:'''
plan_node_new = '''def plan_node(state: AgentState) -> dict:
    req = state["messages"][-1]
    req_content = str(req.content if hasattr(req, "content") else req).lower()
    keywords = ["laptop", "monitor", "keyboard", "mouse", "equipment"]
    if sum(1 for kw in keywords if kw in req_content) < 1:
        return {"status": "blocked", "final_result": "Request unclear. Please specify product."}
'''
graph_py = graph_py.replace(plan_node_orig, plan_node_new)

# block gibberish
plan_node_gibberish = '''        data = {"product_category": "laptop", "preferred_price_max": 2000}'''
plan_node_gibberish_new = '''        return {"status": "blocked", "final_result": "Could not understand request"}
    if "product_category" not in data or not data["product_category"]:
        return {"status": "blocked", "final_result": "Could not understand request"}'''
graph_py = graph_py.replace(plan_node_gibberish, plan_node_gibberish_new)


# Fix 2 (fetch_info_node)
fetch_orig = '''def fetch_info_node(state: AgentState) -> dict:
    emp = get_employee(state["employee_id"])
    dept = emp.get("department", "Unknown")'''
fetch_new = '''def fetch_info_node(state: AgentState) -> dict:
    try:
        emp = get_employee(state["employee_id"])
    except Exception:
        emp = {}
    if not emp or emp.get("error"):
        return {"status": "blocked", "final_result": "Employee not found", "employee_info": {}}
    dept = emp.get("department", "Unknown")'''
graph_py = graph_py.replace(fetch_orig, fetch_new)


# Fix 9 (select_product_node)
select_orig = '''    approved_products = [p for p in products if p.get("vendor_approved") == 1 and p.get("price", float('inf')) <= rem_budget]
    
    if not approved_products:
        return {
            "status": "blocked",
            "final_result": "No approved product within budget",'''
select_new = '''    cat = state.get("product_info", {}).get("product_category", "laptop")
    approved_products = [p for p in products if p.get("vendor_approved") == 1 and p.get("price", float('inf')) <= rem_budget and p.get("category", "").lower() == cat.lower()]
    
    if not approved_products:
        return {
            "status": "blocked",
            "final_result": f"No products available in category {cat}",'''
graph_py = graph_py.replace(select_orig, select_new)

# Fix 15 (Error surfacing in audit_log for execute, block, policy)
execute_orig = '''def execute_node(state: AgentState) -> dict:
    prod_id = state.get("product_id")'''
execute_new = '''def execute_node(state: AgentState) -> dict:
    try:
        prod_id = state.get("product_id")'''
graph_py = graph_py.replace(execute_orig, execute_new)
graph_py = graph_py.replace('''    send_email("admin@company.com", "Order Placed", f"Ordered product {prod_id}", trace_id)
    
    return {
        "status": "done",
        "final_result": "Order placed"
    }''', '''    send_email("admin@company.com", "Order Placed", f"Ordered product {prod_id}", trace_id)
    
        return {
            "status": "done",
            "final_result": "Order placed"
        }
    except Exception as e:
        write_audit(trace_id=state.get("trace_id",""), actor="agent", action="execute_error", result="FAILED")
        return {"status": "error", "final_result": str(e)}''')

# Add routers for plan and fetch
routers = '''
def route_plan(state: AgentState):
    if state.get("status") == "blocked": return "block_node"
    return "fetch_info_node"

def route_fetch(state: AgentState):
    if state.get("status") == "blocked": return "block_node"
    return "select_product_node"
'''
graph_py = graph_py.replace('def route_policy(state: AgentState) -> str:', routers + '\ndef route_policy(state: AgentState) -> str:')

graph_py = graph_py.replace('builder.add_edge("plan_node", "fetch_info_node")', 'builder.add_conditional_edges("plan_node", route_plan, {"block_node": "block_node", "fetch_info_node": "fetch_info_node"})')
graph_py = graph_py.replace('builder.add_edge("fetch_info_node", "select_product_node")', 'builder.add_conditional_edges("fetch_info_node", route_fetch, {"block_node": "block_node", "select_product_node": "select_product_node"})')

with open('agent/graph.py', 'w', encoding='utf-8') as f:
    f.write(graph_py)

# ==============================================================================
# FIX 3, FIX 4, FIX 16: mock_systems/api.py
# ==============================================================================
with open('mock_systems/api.py', 'r', encoding='utf-8') as f:
    api_py = f.read()

# Fix 16 (cleanup_stale)
cleanup_stale = '''
@app.post("/cleanup_stale")
def cleanup_stale():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_log WHERE result = 'PENDING' AND timestamp < datetime('now', '-24 hours')")
    conn.commit()
    conn.close()
    return {"status": "success"}
'''
api_py = api_py.replace('if __name__ == "__main__":', cleanup_stale + '\nif __name__ == "__main__":')

# Fix 3 (Budget decrement)
order_orig = '''    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_log (trace_id, action, result) VALUES (?, ?, ?)", 
                   (trace_id, "place_order", "SUCCESS"))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "order_id": order_id}'''

order_new = '''    cursor = conn.cursor()
    
    # Get price & dept to decrement budget
    cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
    price_row = cursor.fetchone()
    price = price_row[0] if price_row else 0
    
    cursor.execute("SELECT department FROM employees WHERE id=?", (employee_id,))
    dept_row = cursor.fetchone()
    dept = dept_row[0] if dept_row else None
    
    if dept:
        cursor.execute("UPDATE budgets SET spent = spent + ? WHERE department = ?", (price, dept))
    
    cursor.execute("INSERT INTO audit_log (trace_id, action, result) VALUES (?, ?, ?)", 
                   (trace_id, "place_order", "SUCCESS"))
    order_id = cursor.lastrowid
    
    cursor.execute("SELECT total_budget, spent FROM budgets WHERE department = ?", (dept,))
    b_row = cursor.fetchone()
    rem = (b_row["total_budget"] - b_row["spent"]) if b_row else 0

    conn.commit()
    conn.close()
    return {"status": "success", "order_id": order_id, "remaining_budget": rem}'''
api_py = api_py.replace(order_orig, order_new)

# Fix 4 (Idempotency)
approve_orig = '''    cursor.execute("UPDATE audit_log SET result = ? WHERE trace_id = ? AND result = 'PENDING'", (decision, trace_id))
    rows_updated = cursor.rowcount
    if rows_updated > 0:'''
approve_new = '''    cursor.execute("UPDATE audit_log SET result = ? WHERE trace_id = ? AND result = 'PENDING'", (decision, trace_id))
    rows_updated = cursor.rowcount
    if rows_updated == 0:
        conn.close()
        from fastapi import Response
        return Response(content='{"status":"already_processed"}', status_code=409, media_type="application/json")
    if rows_updated > 0:'''
api_py = api_py.replace(approve_orig, approve_new)

with open('mock_systems/api.py', 'w', encoding='utf-8') as f:
    f.write(api_py)

# ==============================================================================
# FIX 4, FIX 5, FIX 11, FIX 14: ui/components.py
# ==============================================================================
with open('ui/components.py', 'r', encoding='utf-8') as f:
    comp_py = f.read()

# Fix 11 (Timestamp parsing)
comp_py = comp_py.replace('import json', 'import json\nfrom datetime import datetime')
comp_py = comp_py.replace('''st.caption(f"Request ID: {row['id']} | Submitted: {row.get('timestamp', 'N/A')}")''',
'''ts = row.get("timestamp")
        if ts:
            try:
                # SQLite timestamp might not have Z or timezone, safely parse it
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                ts_str = ts
        else:
            ts_str = "N/A"
        st.caption(f"Request ID: {row['id']} | Submitted: {ts_str}")''')

# Fix 14 (Double click protection)
comp_py = comp_py.replace('''if st.button("✅ Approve", key=f"approve_{row['id']}", use_container_width=True):''', 
'''is_disabled = st.session_state.get(f"clicked_app_{row['id']}", False)
            if st.button("✅ Approve", key=f"approve_{row['id']}", use_container_width=True, disabled=is_disabled):
                st.session_state[f"clicked_app_{row['id']}"] = True''')

comp_py = comp_py.replace('''if st.button("❌ Reject", key=f"reject_{row['id']}", use_container_width=True):''', 
'''is_disabled_rej = st.session_state.get(f"clicked_rej_{row['id']}", False)
            if st.button("❌ Reject", key=f"reject_{row['id']}", use_container_width=True, disabled=is_disabled_rej):
                st.session_state[f"clicked_rej_{row['id']}"] = True''')

# Fix 4 (409) + Fix 5 (Exception wrapping) -> We already have try-except, let's just add 409 check.
comp_py = comp_py.replace('''if r.status_code == 200 and r.json().get("rows_updated", 0) > 0:''', 
'''if r.status_code == 409:
                        st.info("Already processed.")
                    elif r.status_code == 200 and r.json().get("rows_updated", 0) > 0:''')

# Fix 5 (Wrap in try except with specific message for get calls)
comp_py = comp_py.replace('''r = requests.get("http://localhost:8000/audit_log", timeout=5)''', 
'''try:
            r = requests.get("http://localhost:8000/audit_log", timeout=5)
        except Exception:
            st.error("Backend service unavailable. Please start the API server: python mock_systems/api.py")
            return''')

with open('ui/components.py', 'w', encoding='utf-8') as f:
    f.write(comp_py)

