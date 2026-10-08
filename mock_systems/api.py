import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import FastAPI, HTTPException
from mock_systems.database import get_connection

app = FastAPI()

@app.get("/employee/{employee_id}")
def get_employee(employee_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(row)

@app.get("/budget/{department}")
def get_budget(department: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM budgets WHERE department = ?", (department,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Department not found")
    d = dict(row)
    d["remaining"] = d["total_budget"] - d["spent"]
    return d

@app.get("/vendors")
def get_vendors():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/products")
def get_products(category: str = None):
    conn = get_connection()
    query = """
        SELECT p.id, p.name, p.category, p.price, p.vendor_id, 
               v.approved as vendor_approved, v.name as vendor_name
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
    """
    params = []
    if category:
        query += " WHERE p.category = ?"
        params.append(category)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/order")
def place_order(payload: dict):
    product_id = payload.get("product_id")
    employee_id = payload.get("employee_id")
    trace_id = payload.get("trace_id", "")
    
    conn = get_connection()
    cursor = conn.cursor()
    
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
    return {"status": "success", "order_id": order_id, "remaining_budget": rem}

@app.post("/send_email")
def send_email(payload: dict):
    trace_id = payload.get("trace_id", "")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_log (trace_id, action, result) VALUES (?, ?, ?)", 
                   (trace_id, "send_email", "SUCCESS"))
    conn.commit()
    conn.close()
    return {"status": "sent"}

@app.get("/audit_log")
def get_audit_log():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/pending")
def get_pending():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM audit_log WHERE policy_verdict = 'REQUIRE_HUMAN_APPROVAL' AND result = 'PENDING' ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/approve")
def approve_request(payload: dict):
    trace_id = payload.get("trace_id")
    decision = payload.get("decision")
    approver = payload.get("approver_id")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_log SET result = ? WHERE trace_id = ? AND result = 'PENDING'", (decision, trace_id))
    rows_updated = cursor.rowcount
    if rows_updated == 0:
        conn.close()
        from fastapi import Response
        return Response(content='{"status":"already_processed"}', status_code=409, media_type="application/json")
    if rows_updated > 0:
        cursor.execute("INSERT INTO audit_log (trace_id, action, result, actor, policy_verdict) VALUES (?, ?, ?, ?, ?)", 
                       (trace_id, "human_approval", decision, approver, f"HUMAN_{decision}"))
    conn.commit()
    conn.close()
    
    if decision == "APPROVED":
        import sys as sys_local, os as os_local
        sys_local.path.insert(0, os_local.path.abspath(os_local.path.join(os_local.path.dirname(__file__), "..")))
        from agent.main import resume
        try:
            resume(trace_id)
        except Exception as e:
            print(f"Resume failed: {e}")
            
    return {"status": "success", "rows_updated": rows_updated}

@app.post("/execute-approved")
def execute_approved(payload: dict):
    trace_id = payload.get("trace_id", "")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_log (trace_id, action, result) VALUES (?, ?, ?)", 
                   (trace_id, "execute_approved_order", "SUCCESS"))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/cleanup_stale")
def cleanup_stale():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_log WHERE result = 'PENDING' AND timestamp < datetime('now', '-24 hours')")
    conn.commit()
    conn.close()
    return {"status": "success"}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
