import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import requests
import pandas as pd
from agent.main import run
from ui.components import render_agent_result, render_audit_table, render_approval_card

st.set_page_config(page_title="Policy-Gated Enterprise Execution System", layout="wide")
st.title("Policy-Gated Enterprise Execution System")

tab1, tab2, tab3 = st.tabs(['Submit Request', 'Pending Approvals', 'Audit Log'])


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

    if 'last_result' in st.session_state:
        res = st.session_state['last_result']
        render_agent_result(res)

with tab2:
    st.header("Manager Approvals")
    st.caption("Review and approve high-risk actions flagged by the policy engine.")
    try:
        resp = requests.get('http://localhost:8000/pending', timeout=5)
        if resp.status_code == 200:
            pending = resp.json()
            if not pending:
                st.info("✅ No pending approvals. All caught up.")
            else:
                deduped = {}
                for row in pending:
                    tid = row["trace_id"]
                    if tid not in deduped or row["id"] > deduped[tid]["id"]:
                        deduped[tid] = row
                for row in deduped.values():
                    render_approval_card(row)
        else:
            st.error('Failed to fetch pending approvals.')
    except Exception as e:
        st.error(f'Mock API is not running. Error: {e}')

with tab3:
    st.header('Audit Log')
    st.caption("🔒 Audit log is append-only. Rows cannot be deleted or modified.")
    render_audit_table()
