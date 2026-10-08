import sys
with open('ui/components.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'st.success("Approved. Agent will proceed.")',
    'st.success(f"✅ Approved. Agent has resumed and completed the workflow. Check Audit Log tab.")'
)

with open('ui/components.py', 'w', encoding='utf-8') as f:
    f.write(content)
