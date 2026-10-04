from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    employee_id: int
    employee_info: dict
    department: str
    remaining_budget: float
    products: list
    product_id: int
    product_info: dict
    cost: float
    vendor_approved: bool
    policy_verdict: str
    policy_rule: str
    trace_id: str
    status: str
    human_decision: str
    final_result: str
