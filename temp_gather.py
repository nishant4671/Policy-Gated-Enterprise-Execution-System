import pandas as pd
import json
import sqlite3
import yaml

# results.csv
df = pd.read_csv('results/results.csv')
safe_correct = df[df['mode'] == 'safe']['correct'].sum()
naive_correct = df[df['mode'] == 'naive']['correct'].sum()
safe_unauth = len(df[(df['mode'] == 'safe') & (df['verdict'] == 'ALLOW') & (df['expected_verdict'] != 'ALLOW')])
naive_unauth = len(df[(df['mode'] == 'naive') & (df['verdict'] == 'ALLOW') & (df['expected_verdict'] != 'ALLOW')])

print(f"Scenarios: {len(df[df['mode']=='safe'])}")
print(f"Safe Correct: {safe_correct}, Naive Correct: {naive_correct}")
print(f"Safe Unauth: {safe_unauth}, Naive Unauth: {naive_unauth}")

# DB
conn = sqlite3.connect('mock_systems/enterprise.db')
print('Rows:', conn.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0])
print('Traces:', conn.execute('SELECT COUNT(DISTINCT trace_id) FROM audit_log').fetchone()[0])

# YAML
with open('policy_engine/policy.yaml', 'r') as f:
    pol = yaml.safe_load(f)
print(f"Rules: {len(pol.get('rules', []))}")
