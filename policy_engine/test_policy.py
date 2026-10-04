import pytest
from policy_engine.engine import check_policy

def test_purchase_allow():
    ctx = {"cost": 500, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "ALLOW"

def test_purchase_high_value():
    ctx = {"cost": 2500, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "REQUIRE_HUMAN_APPROVAL"

def test_purchase_unapproved_vendor():
    ctx = {"cost": 500, "vendor_approved": False, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "BLOCK"

def test_intern_limit_exceeded():
    ctx = {"cost": 600, "vendor_approved": True, "employee_role": "Intern", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "BLOCK"

def test_intern_limit_allowed():
    ctx = {"cost": 400, "vendor_approved": True, "employee_role": "Intern", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "ALLOW"

def test_budget_exceeded():
    ctx = {"cost": 500, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 100}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "BLOCK"

def test_forbidden_action_delete():
    ctx = {"cost": 0, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("delete_employee", ctx)
    assert res["verdict"] == "BLOCK"

def test_forbidden_action_admin():
    ctx = {"cost": 0, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("grant_admin", ctx)
    assert res["verdict"] == "BLOCK"

def test_boundary_1000():
    ctx = {"cost": 1000, "vendor_approved": True, "employee_role": "Engineer", "remaining_budget": 10000}
    res = check_policy("purchase", ctx)
    assert res["verdict"] == "ALLOW"

def test_missing_context():
    res = check_policy("purchase", {})
    assert res["verdict"] == "BLOCK"
    assert res["rule"] == "evaluation_error"
