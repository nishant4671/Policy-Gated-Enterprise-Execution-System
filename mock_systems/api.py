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
    cursor.execute("INSERT INTO audit_log (trace_id, action, result) VALUES (?, ?, ?)", 
                   (trace_id, "place_order", "SUCCESS"))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "order_id": order_id}

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
    if rows_updated > 0:
        cursor.execute("INSERT INTO audit_log (trace_id, action, result, actor, policy_verdict) VALUES (?, ?, ?, ?, ?)", 
                       (trace_id, "human_approval", decision, approver, f"HUMAN_{decision}"))
    conn.commit()
    conn.close()
    return {"status": "success", "rows_updated": rows_updated}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
