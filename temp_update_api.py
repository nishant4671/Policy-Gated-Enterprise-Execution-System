import sys
with open('mock_systems/api.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''    conn.commit()
    conn.close()
    
    if decision == "APPROVED":
        import sys as sys_local, os as os_local
        sys_local.path.insert(0, os_local.path.abspath(os_local.path.join(os_local.path.dirname(__file__), "..")))
        from agent.main import resume
        try:
            resume(trace_id)
        except Exception as e:
            print(f"Resume failed: {e}")
            
    return {"status": "success", "rows_updated": rows_updated}'''

content = content.replace('''    conn.commit()
    conn.close()
    return {"status": "success", "rows_updated": rows_updated}''', replacement)

with open('mock_systems/api.py', 'w', encoding='utf-8') as f:
    f.write(content)
