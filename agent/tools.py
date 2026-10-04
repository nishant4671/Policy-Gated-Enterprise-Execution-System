import requests
import json
from datetime import datetime, timezone
from mock_systems.database import get_connection

BASE_URL = "http://localhost:8000"
TIMEOUT = 5

def get_employee(employee_id: int) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/employee/{employee_id}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def check_budget(department: str) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/budget/{department}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def list_products(category: str) -> list:
    try:
        r = requests.get(f"{BASE_URL}/products", params={"category": category}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def place_order(product_id: int, employee_id: int, trace_id: str) -> dict:
    try:
        payload = {"product_id": product_id, "employee_id": employee_id, "trace_id": trace_id}
        r = requests.post(f"{BASE_URL}/order", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def send_email(to: str, subject: str, body: str, trace_id: str) -> dict:
    try:
        payload = {"to": to, "subject": subject, "body": body, "trace_id": trace_id}
        r = requests.post(f"{BASE_URL}/send_email", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def write_audit(trace_id: str, actor: str, action: str, tool_called: str, arguments: str, policy_verdict: str, policy_rule: str, result: str, error: str = None):
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_log 
            (trace_id, timestamp, actor, action, tool_called, arguments, policy_verdict, policy_rule, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trace_id, timestamp, actor, action, tool_called, arguments, policy_verdict, policy_rule, result, error))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}
