import sys
import os
import time
import requests
import json
import yaml
import questionary
import getpass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.main import run as run_agent

console = Console()
API_URL = "http://localhost:8000"
SESSION = {}

def check_api_health() -> bool:
    try:
        requests.get(f"{API_URL}/audit_log", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

def api_status_dot() -> str:
    return "● online" if check_api_health() else "● offline"

def get_pending_count() -> int:
    if not check_api_health(): return 0
    try:
        r = requests.get(f"{API_URL}/pending", timeout=2)
        return len(r.json()) if r.status_code == 200 else 0
    except:
        return 0

def print_banner():
    name = SESSION.get("name", "Unknown")
    dept = SESSION.get("department", "Unknown")
    banner = f" PGEES v1.0.0  |  👤 {name} ({dept})  |  {api_status_dot()} "
    console.print(Panel(banner, border_style="cyan", padding=(0, 2), expand=False))

def print_main_menu():
    role = SESSION.get("role", "employee")
    pending_count = get_pending_count()
    pending_text = f" ({pending_count} pending)" if pending_count > 0 else ""
    
    console.print()
    if role == "intern":
        console.print("MAIN MENU [dim](Intern — $500 limit)[/dim]")
    else:
        console.print("MAIN MENU")
        
    console.print("────────────────────────────────────────────────")
    if role == "manager":
        console.print("[1]  📝  Submit a new request")
        console.print(f"[2]  🛡️   Review pending approvals{pending_text}")
        console.print("[3]  📊  View audit log")
        console.print("[4]  🔍  Search by trace ID")
        console.print("[5]  📋  View policy rules")
        console.print("[6]  ℹ️   About / Help")
        console.print("[7]  🚪  Logout")
        console.print("[8]  ❌  Exit")
    else:
        console.print("[1]  📝  Submit a new request")
        console.print("[2]  👀  View my requests")
        console.print("[3]  📊  View audit log")
        console.print("[4]  📋  View policy rules")
        console.print("[5]  ℹ️   About / Help")
        console.print("[6]  🚪  Logout")
        console.print("[7]  ❌  Exit")
    console.print("────────────────────────────────────────────────")
    console.print()

def prompt_action(options: dict) -> str:
    hint = "  ".join([f"[{k}] {v}" for k, v in options.items()])
    console.print(f"\n[dim]Options: {hint}[/dim]")
    while True:
        raw = console.input("[dim]→ [/dim]").strip().lower()
        if raw in options:
            return raw
        word_map = {
            "back": "b", "menu": "b", "main": "b", "return": "b",
            "repeat": "r", "again": "r",
            "exit": "x", "quit": "x", "q": "x", "e": "x",
            "approve": "a", "reject": "r", "skip": "s",
            "refresh": "r", "filter": "f", "trace": "t",
            "yes": "y", "no": "n",
            "search": "s",
        }
        mapped = word_map.get(raw)
        if mapped and mapped in options:
            return mapped
        console.print(f"[yellow]'{raw}' not recognized. Type one of: {', '.join(options.keys())}[/yellow]")

def submit_request_flow():
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print("📝  SUBMIT A NEW REQUEST")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        req = console.input("Enter request: ").strip()
        if not req:
            console.print("[red]Request cannot be empty.[/red]")
            continue
            
        emp_id = SESSION.get("employee_id")
        name = SESSION.get("name")
        dept = SESSION.get("department")
        console.print(f"\n[dim]Submitting as: {name} ({dept})[/dim]")
            
        with console.status("[bold green]Running agent...[/bold green]", spinner="dots"):
            try:
                result = run_agent(req, emp_id, safe_mode=True)
            except Exception as e:
                console.print(f"[red]❌ Agent error: {e}[/red]")
                result = None
                
        if result:
            status = result.get("status", "unknown")
            verdict = result.get("policy_verdict", "None")
            trace = result.get("trace_id", "Unknown")
            cost = result.get("cost", 0.0)
            
            prod = result.get("product_info", {})
            prod_name = prod.get("name", "Unknown") if isinstance(prod, dict) else "Unknown"
            rule = result.get("policy_rule", "None")
            
            if status in ("done", "ALLOW") or verdict == "ALLOW":
                icon_color = "green"; icon = "✅"; title = "Success"
            elif status == "awaiting_approval" or verdict == "REQUIRE_HUMAN_APPROVAL":
                icon_color = "yellow"; icon = "⚠️"; title = "Awaiting approval"
            else:
                icon_color = "red"; icon = "❌"; title = "Blocked"
                
            panel_content = f"  {icon}  {title}\n  Product: {prod_name}\n  Cost: ${cost:,.2f}\n  Rule: {rule}\n  Trace: {trace}"
            console.print("\n", Panel(panel_content, title="Result", border_style=icon_color, expand=False, padding=(0, 2)))
            
        action = prompt_action({"b": "Back", "r": "Submit another", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def pending_approvals_flow():
    if SESSION.get("role") != "manager":
        console.print("\n[red]❌ Manager access required.[/red]")
        return
        
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        try:
            r = requests.get(f"{API_URL}/pending", timeout=2)
            pending_list = r.json() if r.status_code == 200 else []
        except:
            pending_list = []
            
        console.print(f"🛡️  PENDING APPROVALS  ({len(pending_list)} item{'s' if len(pending_list) != 1 else ''})")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        if not pending_list:
            console.print("No pending approvals.")
            action = prompt_action({"b": "Back", "r": "Refresh list", "x": "Exit"})
            if action == 'b': return
            elif action == 'x': 
                if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)
            continue
            
        for i, item in enumerate(pending_list):
            try: args = json.loads(item.get("arguments", "{}"))
            except: args = {}
                
            prod_name = args.get("product_name", "Unknown")
            cost = args.get("cost", 0.0)
            rule = item.get("rule_triggered") or args.get("rule_triggered") or "Unknown"
            emp = args.get("employee_id", "Unknown")
            dept = args.get("department", "Unknown")
            trace = item.get("trace_id", "Unknown")
            
            console.print(f"[{i+1}/{len(pending_list)}]  {prod_name} — ${cost:,.2f}")
            console.print(f"       Requested by: Employee {emp} ({dept})")
            console.print(f"       Rule: {rule}")
            console.print(f"       Trace: {trace}")
            
            choice = prompt_action({"a": "Approve", "r": "Reject", "s": "Skip", "b": "Back", "x": "Exit"})
            if choice == 'b': return
            if choice == 'x':
                if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)
                else: continue
            if choice == 's': continue
                
            decision = "APPROVED" if choice == 'a' else "REJECTED"
            with console.status(f"[bold cyan]Resuming agent...[/bold cyan]"):
                try:
                    res = requests.post(f"{API_URL}/approve", json={"trace_id": trace, "decision": decision}, timeout=5)
                    if res.status_code == 200:
                        console.print(f"✅ Successfully {decision.lower()} trace {trace}")
                    else:
                        console.print(f"❌ Failed to process decision: {res.text}")
                except Exception as e:
                    console.print(f"❌ Error: {e}")
            
        action = prompt_action({"b": "Back", "r": "Refresh list", "x": "Exit"})
        if action == 'b': return
        elif action == 'x': 
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def audit_log_flow():
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print("📊  AUDIT LOG")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        try:
            r = requests.get(f"{API_URL}/audit_log", timeout=2)
            logs = r.json() if r.status_code == 200 else []
        except:
            logs = []
            
        if not logs:
            console.print("No logs found.")
        else:
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("ID", style="dim")
            table.add_column("Trace ID")
            table.add_column("Action")
            table.add_column("Verdict")
            table.add_column("Result")
            
            for log in logs:
                v = log.get("policy_verdict", "")
                if v == "ALLOW": v = f"[green]{v}[/green]"
                elif v == "BLOCK": v = f"[red]{v}[/red]"
                elif v == "REQUIRE_HUMAN_APPROVAL": v = f"[yellow]HUMAN_APPROVAL[/yellow]"
                
                table.add_row(
                    str(log.get("id")),
                    str(log.get("trace_id"))[:8],
                    str(log.get("action")),
                    v,
                    str(log.get("result", ""))[:40]
                )
            console.print(table)
            
        action = prompt_action({"r": "Refresh", "b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def search_trace_flow():
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print("  🔍  SEARCH BY TRACE ID")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        trace_input = console.input("Enter trace ID to search: ").strip()
        if not trace_input:
            action = prompt_action({"b": "Back", "x": "Exit"})
            if action == 'b': return
            elif action == 'x':
                if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)
            continue
            
        try:
            r = requests.get(f"{API_URL}/audit_log", timeout=2)
            logs = r.json() if r.status_code == 200 else []
        except:
            logs = []
            
        matching_logs = [log for log in logs if str(log.get("trace_id", "")).startswith(trace_input)]
        
        if not matching_logs:
            console.print(f"No rows found for trace '{trace_input}'.")
        else:
            console.print(f"Found {len(matching_logs)} matching actions:")
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("ID", style="dim")
            table.add_column("Action")
            table.add_column("Tool")
            table.add_column("Verdict")
            table.add_column("Result")
            
            for log in matching_logs:
                v = log.get("policy_verdict", "")
                if v == "ALLOW": v = f"[green]{v}[/green]"
                elif v == "BLOCK": v = f"[red]{v}[/red]"
                elif v == "REQUIRE_HUMAN_APPROVAL": v = f"[yellow]HUMAN_APPROVAL[/yellow]"
                
                table.add_row(
                    str(log.get("id")),
                    str(log.get("action")),
                    str(log.get("tool_called", "")),
                    v,
                    str(log.get("result", ""))[:40]
                )
            console.print(table)
            console.print("\nWorkflow Chain:")
            for i, log in enumerate(matching_logs):
                console.print(f"  {i+1}. {log.get('action')} -> {log.get('tool_called')} [{log.get('policy_verdict')}]")
                
        action = prompt_action({"s": "Search again", "b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 's': continue
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def view_policy_rules_flow():
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print("  📋  POLICY RULES")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", "policy_engine", "policy.yaml"), "r") as f:
                policy = yaml.safe_load(f)
            rules = policy.get("rules", [])
            
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Rule Name")
            table.add_column("Condition")
            table.add_column("Verdict")
            
            for rule in rules:
                v = rule.get("verdict", "")
                if v == "ALLOW": v = f"[green]{v}[/green]"
                elif v == "BLOCK": v = f"[red]{v}[/red]"
                elif v == "REQUIRE_HUMAN_APPROVAL": v = f"[yellow]HUMAN_APPROVAL[/yellow]"
                
                table.add_row(rule.get("name", ""), rule.get("condition", ""), v)
                
            console.print(table)
            console.print(f"\nTotal: {len(rules)} rules")
            console.print("Default verdict when no rule matches: ALLOW")
            console.print("On evaluation error: BLOCK (fail-closed)")
            
        except Exception as e:
            console.print(f"[red]Error reading policy rules: {e}[/red]")
            
        action = prompt_action({"b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def about_help_flow():
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print("  ℹ️  ABOUT / HELP")
        console.print("────────────────────────────────────────────────")
        console.print()
        
        content = """  PGEES — Policy-Gated Enterprise Execution System
  Version 1.0.0
  Project Code: FAIR-AI-P03

  WHAT IT DOES:
    A 4-layer agent architecture that safely executes enterprise
    workflows. The LLM plans, a deterministic policy engine decides,
    and a human approves high-risk actions.

  ARCHITECTURE:
    Layer 1 — Mock Enterprise Systems (FastAPI + SQLite)
    Layer 2 — Policy Engine (Python + YAML)
    Layer 3 — LangGraph Agent + LLM (Groq / Gemini)
    Layer 4 — Human-in-the-Loop Gateway (this CLI)

  DEMO ACCOUNTS:
    101 / john123   — Employee (Software Engineer)
    102 / jane123   — Employee (Product Manager)
    103 / bob123    — Intern (Engineering, $500 limit)
    201 / sarah123  — Manager (Engineering Manager)

  AUTHORS:
    Nishant Kumar, Nishita Dhanotiya,
    Shekhar Dwivedi, Hardik Verma"""
        
        console.print(content)
        
        action = prompt_action({"b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def masked_input(prompt: str = "Password: ") -> str:
    """Prompt for password, echo '*' per character."""
    print(prompt, end="", flush=True)
    password = ""
    while True:
        ch = None
        # Windows
        if sys.platform == "win32":
            import msvcrt
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                print()
                break
            elif ch == "\x08":  # backspace
                if password:
                    password = password[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            else:
                password += ch
                sys.stdout.write("*")
                sys.stdout.flush()
        else:
            import getpass as gp
            password = gp.getpass("")
            break
    return password

def login_flow():
    failures = 0
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(" PGEES — Login ", expand=False))
        console.print("\n[dim]Test accounts: 101/john123  102/jane123  103/bob123  201/sarah123[/dim]\n")
        
        emp_id = console.input("Employee ID: ").strip()
        pwd = masked_input("Password: ").strip()
        
        if not emp_id.isdigit():
            console.print("❌ Invalid employee ID format.")
            time.sleep(1)
            failures += 1
            if failures >= 3: sys.exit(1)
            continue
            
        try:
            res = requests.post(f"{API_URL}/login", json={"employee_id": int(emp_id), "password": pwd}, timeout=2)
            if res.status_code == 200:
                data = res.json()
                SESSION["employee_id"] = data["employee_id"]
                SESSION["name"] = data["name"]
                SESSION["role"] = data["role"]
                SESSION["department"] = data["department"]
                console.print(f"\n✅ Welcome, {data['name']} ({data['role'].title()}, {data['department']})")
                time.sleep(1.5)
                return
            else:
                console.print("\n❌ Invalid credentials")
        except Exception as e:
            console.print(f"\n❌ API Error: {e}")
            
        failures += 1
        time.sleep(1.5)
        if failures >= 3:
            console.print("Too many failed attempts. Exiting.")
            sys.exit(1)

def main():
    while True:
        login_flow()
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        while True:
            print_main_menu()
            choice = console.input("Select [1-8]: [dim]→ [/dim]").strip()
            
            role = SESSION.get("role")
            
            if role == "manager":
                if choice == '1': submit_request_flow()
                elif choice == '2': pending_approvals_flow()
                elif choice == '3': audit_log_flow()
                elif choice == '4': search_trace_flow()
                elif choice == '5': view_policy_rules_flow()
                elif choice == '6': about_help_flow()
                elif choice == '7':
                    SESSION.clear()
                    break # Back to login
                elif choice == '8':
                    if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)
                else:
                    console.print("Invalid selection. Please enter 1-8.")
            else:
                if choice == '1': submit_request_flow()
                elif choice == '2': console.print("\n[dim]Feature coming soon.[/dim]")
                elif choice == '3': audit_log_flow()
                elif choice == '4': view_policy_rules_flow()
                elif choice == '5': about_help_flow()
                elif choice == '6':
                    SESSION.clear()
                    break # Back to login
                elif choice == '7':
                    if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)
                else:
                    console.print("Invalid selection. Please enter 1-7.")

if __name__ == "__main__":
    main()
