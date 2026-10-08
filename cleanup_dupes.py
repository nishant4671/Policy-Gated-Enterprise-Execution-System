import sqlite3
conn = sqlite3.connect('mock_systems/enterprise.db')
cur = conn.cursor()
cur.execute("""
    DELETE FROM audit_log
    WHERE result = 'PENDING'
    AND id NOT IN (
        SELECT MAX(id) FROM audit_log
        WHERE result = 'PENDING'
        GROUP BY trace_id
    )
""")
conn.commit()
print(f"Deleted {cur.rowcount} duplicate rows")
conn.close()
