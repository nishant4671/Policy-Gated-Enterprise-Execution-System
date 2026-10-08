import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime

def render_agent_result(res):
    status = res.get('status', 'unknown')
    verdict = res.get('policy_verdict', 'N/A')
    cost = res.get('cost', 0)
    if cost is None: cost = 0
    
    product_info = res.get('product_info', {})
    if not isinstance(product_info, dict):
        product_info = {}
        
    product_name = product_info.get('name', 'N/A')
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", status)
    col2.metric("Verdict", verdict)
    col3.metric("Cost", f"${cost:,.2f}")
    col4.metric("Product", product_name)
    
    if "remaining_budget" in res and res["remaining_budget"] is not None:
        st.metric("Department Budget Remaining", f"${res['remaining_budget']:,.0f}")
        
    with st.expander("Summary", expanded=True):
        emp_info = res.get('employee_info', {})
        if not isinstance(emp_info, dict):
            emp_info = {}
            
        emp_name = emp_info.get('name', 'Unknown')
        emp_role = emp_info.get('role', 'Unknown')
        emp_dept = res.get('department', 'Unknown')
        vendor = product_info.get('vendor_name', 'N/A')
        rule = res.get('policy_rule', 'None')
        
        st.write(f"**Employee:** {emp_name} ({emp_role}, {emp_dept})")
        st.write(f"**Product:** {product_name} (Vendor: {vendor}) - ${cost:,.2f}")
        st.write(f"**Policy Rule:** {rule} -> **{verdict}**")
        
        if status == "awaiting_approval":
            st.warning("Waiting for manager approval")
        elif status == "blocked":
            st.error(f"Blocked: {rule}")
        elif status == "done":
            st.success("Order placed successfully")
            
    with st.expander("Technical Details (for debugging)", expanded=False):
        st.json(res)

def render_agent_trace(status, verdict, rule, final):
    st.markdown("### Agent Trace")
    st.write(f"**Status:** {status}")
    st.write(f"**Verdict:** {verdict}")
    st.write(f"**Rule:** {rule}")
    st.write(f"**Final:** {final}")

def render_audit_table():
    try:
        try:
            r = requests.get("http://localhost:8000/audit_log", timeout=5)
        except Exception:
            st.error("Backend service unavailable. Please start the API server: python mock_systems/api.py")
            return
        df = pd.DataFrame(r.json())
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load audit log: {e}")

def render_approval_card(row):
    try:
        args = json.loads(row.get("arguments", "{}"))
    except Exception:
        args = {}
        
    product_name = args.get("product_name", "Unknown Product")
    employee_id = args.get("employee_id", "Unknown")
    cost = args.get("cost", 0.0)
    if cost is None: cost = 0.0
    
    emp_name = f"Employee {employee_id}"
    emp_dept = "Unknown Dept"
    try:
        emp_resp = requests.get(f"http://localhost:8000/employee/{employee_id}", timeout=2)
        if emp_resp.status_code == 200:
            emp_data = emp_resp.json()
            emp_name = emp_data.get("name", emp_name)
            emp_dept = emp_data.get("department", emp_dept)
    except Exception:
        pass
    
    with st.container(border=True):
        st.subheader(f"🛑 Approval Required — {product_name}")
        st.write(f"Employee **{emp_name} ({emp_dept})** wants to buy: **{product_name}**")
        st.metric("Cost", f"${float(cost):,.2f}")
        
        st.write(f"**Why flagged:** Purchase exceeds $1,000 auto-approval limit")
        st.warning("This request needs your approval before the agent can proceed.")
        
        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
        with btn_col1:
            is_disabled = st.session_state.get(f"clicked_app_{row['id']}", False)
            if st.button("✅ Approve", key=f"approve_{row['id']}", use_container_width=True, disabled=is_disabled):
                st.session_state[f"clicked_app_{row['id']}"] = True
                try:
                    r = requests.post(
                        "http://localhost:8000/approve",
                        json={
                            "trace_id": row["trace_id"],
                            "approver_id": "manager_201",
                            "decision": "APPROVED"
                        },
                        timeout=5
                    )
                    if r.status_code == 409:
                        st.info("Already processed.")
                    elif r.status_code == 200 and r.json().get("rows_updated", 0) > 0:
                        try:
                            requests.post(
                                "http://localhost:8000/execute-approved",
                                json={"trace_id": row["trace_id"]},
                                timeout=5
                            )
                        except Exception:
                            pass
                        st.success(f"✅ Approved. Agent has resumed and completed the workflow. Check Audit Log tab.")
                        st.rerun()
                    else:
                        st.error(f"Approval failed: {r.text}")
                except Exception as e:
                    st.error(f"Approval error: {e}")

        with btn_col2:
            is_disabled_rej = st.session_state.get(f"clicked_rej_{row['id']}", False)
            if st.button("❌ Reject", key=f"reject_{row['id']}", use_container_width=True, disabled=is_disabled_rej):
                st.session_state[f"clicked_rej_{row['id']}"] = True
                try:
                    r = requests.post(
                        "http://localhost:8000/approve",
                        json={
                            "trace_id": row["trace_id"],
                            "approver_id": "manager_201",
                            "decision": "REJECTED"
                        },
                        timeout=5
                    )
                    if r.status_code == 409:
                        st.info("Already processed.")
                    elif r.status_code == 200 and r.json().get("rows_updated", 0) > 0:
                        st.warning("Rejected. Agent will not proceed.")
                        st.rerun()
                    else:
                        st.error(f"Rejection failed: {r.text}")
                except Exception as e:
                    st.error(f"Rejection error: {e}")
                    
        ts = row.get("timestamp")
        if ts:
            try:
                # SQLite timestamp might not have Z or timezone, safely parse it
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                ts_str = ts
        else:
            ts_str = "N/A"
        st.caption(f"Request ID: {row['id']} | Submitted: {ts_str}")
