import streamlit as st
import requests
import pandas as pd

def render_agent_trace(status, verdict, rule, final):
    st.markdown("### Agent Trace")
    st.write(f"**Status:** {status}")
    st.write(f"**Verdict:** {verdict}")
    st.write(f"**Rule:** {rule}")
    st.write(f"**Final:** {final}")

def render_audit_table():
    try:
        r = requests.get("http://localhost:8000/audit_log", timeout=5)
        df = pd.DataFrame(r.json())
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load audit log: {e}")

def render_approval_card(row):
    with st.container(border=True):
        st.markdown(f"**Request #{row['id']}** — {row['action']}")
        st.write(f"Trace: {row['trace_id']}")
        st.write(f"Arguments: {row['arguments']}")
        st.write(f"Rule triggered: {row['policy_rule']}")
        
        st.write("---")
        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
        with btn_col1:
            if st.button("✅ Approve", key=f"approve_{row['id']}", use_container_width=True):
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
                    if r.status_code == 200 and r.json().get("rows_updated", 0) > 0:
                        st.success(f"✅ Approved trace {row['trace_id'][:8]}")
                        st.rerun()
                    else:
                        st.error(f"Approval failed: {r.text}")
                except Exception as e:
                    st.error(f"Approval error: {e}")

        with btn_col2:
            if st.button("❌ Reject", key=f"reject_{row['id']}", use_container_width=True):
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
                    if r.status_code == 200 and r.json().get("rows_updated", 0) > 0:
                        st.warning(f"❌ Rejected trace {row['trace_id'][:8]}")
                        st.rerun()
                    else:
                        st.error(f"Rejection failed: {r.text}")
                except Exception as e:
                    st.error(f"Rejection error: {e}")
