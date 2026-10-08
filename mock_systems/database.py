import sqlite3
import os

DB_PATH = "mock_systems/enterprise.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT,
        role TEXT,
        department TEXT,
        manager_id INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        department TEXT PRIMARY KEY,
        total_budget REAL,
        spent REAL DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY,
        name TEXT,
        approved INTEGER DEFAULT 1
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        vendor_id INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trace_id TEXT,
        timestamp TEXT,
        actor TEXT,
        actor_id TEXT,
        action TEXT,
        tool_called TEXT,
        arguments TEXT,
        policy_verdict TEXT,
        policy_rule TEXT,
        human_approver TEXT,
        result TEXT,
        error TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        employee_id INTEGER PRIMARY KEY,
        password TEXT NOT NULL, -- Demo limitation: passwords stored in plain text
        role TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    ''')

    # Idempotent cleanup
    cursor.execute('DELETE FROM employees')
    cursor.execute('DELETE FROM budgets')
    cursor.execute('DELETE FROM vendors')
    cursor.execute('DELETE FROM products')
    cursor.execute('DELETE FROM audit_log')
    cursor.execute('DELETE FROM users')

    # Seed data
    employees_data = [
        (101, "John Doe", "Software Engineer", "Engineering", 201),
        (102, "Jane Smith", "Product Manager", "Product", 201),
        (103, "Bob Wilson", "Intern", "Engineering", 101),
        (201, "Sarah Chen", "Engineering Manager", "Engineering", None)
    ]
    cursor.executemany('INSERT INTO employees (id, name, role, department, manager_id) VALUES (?, ?, ?, ?, ?)', employees_data)
    
    users_data = [
        (101, "john123", "employee"),
        (102, "jane123", "employee"),
        (103, "bob123", "intern"),
        (201, "sarah123", "manager")
    ]
    cursor.executemany('INSERT INTO users (employee_id, password, role) VALUES (?, ?, ?)', users_data)

    budgets_data = [
        ("Engineering", 50000.0, 12000.0),
        ("Product", 30000.0, 5000.0)
    ]
    cursor.executemany('INSERT INTO budgets (department, total_budget, spent) VALUES (?, ?, ?)', budgets_data)

    vendors_data = [
        (1, "Dell", 1),
        (2, "Apple", 1),
        (3, "Lenovo", 1),
        (4, "CheapLaptops Inc", 0)
    ]
    cursor.executemany('INSERT INTO vendors (id, name, approved) VALUES (?, ?, ?)', vendors_data)

    products_data = [
        (1, "Dell Latitude 5540", "laptop", 850.0, 1),
        (2, "MacBook Pro 14", "laptop", 1999.0, 2),
        (3, "Lenovo ThinkPad X1", "laptop", 1450.0, 3),
        (4, "Dell 27 Monitor", "monitor", 320.0, 1),
        (5, "MacBook Air M3", "laptop", 1099.0, 2),
        (6, "CheapBook 3000", "laptop", 400.0, 4)
    ]
    cursor.executemany('INSERT INTO products (id, name, category, price, vendor_id) VALUES (?, ?, ?, ?, ?)', products_data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialized")
