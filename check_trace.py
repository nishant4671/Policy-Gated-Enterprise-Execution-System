import sqlite3
c = sqlite3.connect("mock_systems/enterprise.db")
rows = c.execute("SELECT action, tool_called, result FROM audit_log WHERE trace_id=? ORDER BY id", ("50525ec1-90cf-4d1e-ae17-38e149c408a1",)).fetchall()
for r in rows: print(r)
c.close()
