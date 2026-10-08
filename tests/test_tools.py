import pytest
import requests
from agent.tools import get_employee, check_budget, list_products, place_order, send_email, write_audit

def is_api_alive():
    try:
        requests.get("http://localhost:8000/vendors", timeout=1)
        return True
    except:
        return False

@pytest.fixture(autouse=True)
def skip_if_api_down():
    if not is_api_alive():
        pytest.skip("API is not running")

def test_get_employee():
    res = get_employee(101)
    assert "error" not in res
    assert res["name"] == "John Doe"

def test_check_budget():
    import sqlite3
    conn = sqlite3.connect('mock_systems/enterprise.db')
    conn.execute("UPDATE budgets SET spent = 12000.0 WHERE department = 'Engineering'")
    conn.commit()
    conn.close()
    
    res = check_budget("Engineering")
    assert "error" not in res
    assert res["remaining"] == 38000.0

def test_list_products():
    res = list_products("laptop")
    assert type(res) == list
    assert len(res) >= 5

def test_place_order():
    res = place_order(1, 101, "test-trace-001")
    assert "error" not in res
    assert res["status"] == "success"

def test_send_email():
    res = send_email("test@x.com", "Hi", "Body", "test-trace-002")
    assert "error" not in res
    assert res["status"] == "sent"

def test_write_audit():
    res = write_audit(
        trace_id="test-trace-003",
        actor="agent",
        action="test",
        tool_called="test_tool",
        arguments="{}",
        policy_verdict="ALLOW",
        policy_rule="default",
        result="SUCCESS"
    )
    assert type(res) == dict
    assert "error" not in res
    assert res.get("status") == "success"
