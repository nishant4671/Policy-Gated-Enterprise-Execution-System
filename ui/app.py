import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import requests
import pandas as pd
from agent.main import run
from ui.components import render_agent_trace, render_audit_table, render_approval_card

st.set_page_config(page_title='SafeGuard-AI', layout='wide')
st.title('🛡️ SafeGuard-AI — Enterprise Agent Console')

tab1, tab2, tab3 = st.tabs(['Submit Request', 'Pending Approvals', 'Audit Log'])

with tab1:
    st.header('Submit Request')
    request_text = st.text_input('Request', value='Buy a laptop')
    emp_id = st.number_input('Employee ID', value=101, min_value=100)
    
    if st.button('Submit'):
        with st.spinner('Agent is planning...'):
            result = run(request_text, int(emp_id), safe_mode=True)
            st.session_state['last_result'] = result
            
    if 'last_result' in st.session_state:
        res = st.session_state['last_result']
        status = res.get('status')
        
        if status == 'done':
            st.success('Request processed successfully.')
        elif status == 'awaiting_approval':
            st.warning('Go to Pending Approvals tab to approve.')
        elif status == 'blocked':
            st.error('Request was blocked by policy.')
        elif status == 'error':
            st.error(f'Error: {res.get("final_result")}')
        else:
            st.info(f'Status: {status}')
            
        with st.expander('View Result Details'):
            st.json(res)

with tab2:
    st.header('Pending Approvals')
    try:
        resp = requests.get('http://localhost:8000/pending', timeout=5)
        if resp.status_code == 200:
            pending = resp.json()
            if not pending:
                st.info('No pending approvals.')
            else:
                for row in pending:
                    render_approval_card(row)
        else:
            st.error('Failed to fetch pending approvals.')
    except Exception as e:
        st.error(f'Mock API is not running. Error: {e}')

with tab3:
    st.header('Audit Log')
    render_audit_table()
