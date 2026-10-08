import sys
import os
import time
import requests
import json
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.main import run as run_agent

console = Console()
API_URL = "http://localhost:8000"

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
    banner = (
        f"  PGEES — Policy-Gated Enterprise Execution System  v1.0.0    \n"
        f"  user: manager_201                     API: {api_status_dot()}         "
    )
    console.print(Panel(banner, border_style="cyan", padding=(0, 2), expand=False))

def print_main_menu():
    pending_count = get_pending_count()
    pending_text = f" ({pending_count} pending)" if pending_count > 0 else ""
    console.print()
    console.print("MAIN MENU")
    console.print("────────────────────────────────────────────────")
    console.print("[1]  📝  Submit a new request")
    console.print(f"[2]  🛡️   Review pending approvals{pending_text}")
    console.print("[3]  📊  View audit log")
    console.print("[4]  🔍  Search by trace ID")
    console.print("[5]  📋  View policy rules")
    console.print("[6]  ℹ️   About / Help")
    console.print("[7]  ❌  Exit")
    console.print("────────────────────────────────────────────────")
    console.print()

def prompt_action(options: dict) -> str:
    """options is like {'b': 'Back to Main Menu', 'r': 'Repeat', 'x': 'Exit'}"""
    hint = "  ".join([f"[{k}] {v}" for k, v in options.items()])
    console.print(f"\n[dim]Options: {hint}[/dim]")
    while True:
        raw = console.input("[dim]→ [/dim]").strip().lower()
        if raw in options:
            return raw
        # accept full-word aliases
        word_map = {
            "back": "b", "menu": "b", "main": "b", "return": "b",
            "repeat": "r", "again": "r",
            "exit": "x", "quit": "x", "q": "x", "e": "x",
            "approve": "a", "reject": "r", "skip": "s",
            "refresh": "r", "filter": "f", "trace": "t",
            "yes": "y", "no": "n",
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
            
        emp_id_str = console.input("Enter employee ID [101]: ").strip()
        if not emp_id_str:
            emp_id_str = "101"
            
        if not emp_id_str.isdigit():
            console.print("[red]Employee ID must be a number.[/red]")
            continue
            
        console.print()
        with console.status("[bold green]Running agent...[/bold green]", spinner="dots"):
            try:
                result = run_agent(req, int(emp_id_str), safe_mode=True)
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
                icon_color = "green"
                icon = "✅"
                title = "Success"
            elif status == "awaiting_approval" or verdict == "REQUIRE_HUMAN_APPROVAL":
                icon_color = "yellow"
                icon = "⚠️"
                title = "Awaiting approval"
            else:
                icon_color = "red"
                icon = "❌"
                title = "Blocked"
                
            panel_content = f"  {icon}  {title}\n  Product: {prod_name}\n  Cost: ${cost:,.2f}\n  Rule: {rule}\n  Trace: {trace}"
            console.print()
            console.print(Panel(panel_content, title="Result", border_style=icon_color, expand=False, padding=(0, 2)))
            
        action = prompt_action({"b": "Back", "r": "Submit another", "x": "Exit"})
        if action == 'b':
            return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask():
                sys.exit(0)

def pending_approvals_flow():
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
            try:
                args = json.loads(item.get("arguments", "{}"))
            except:
                args = {}
                
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
            if choice == 's':
                continue
                
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
            
            for log in logs[-20:]:
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
            
        action = prompt_action({"r": "Refresh", "f": "Filter by verdict", "t": "Filter by trace", "b": "Back", "x": "Exit"})
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

  POLICY VERDICTS:
    ALLOW                  → Execute automatically
    REQUIRE_HUMAN_APPROVAL → Pause and wait for manager
    BLOCK                  → Reject and log

  NAVIGATION:
    1  Submit a new request
    2  Review pending approvals
    3  View audit log
    4  Search by trace ID
    5  View policy rules
    6  About / Help
    7  Exit

  AUTHORS:
    Nishant Kumar, Nishita Dhanotiya,
    Shekhar Dwivedi, Hardik Verma"""
        
        console.print(content)
        
        action = prompt_action({"b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def placeholder_flow(title):
    while True:
        console.print()
        console.print("────────────────────────────────────────────────")
        console.print(f"  {title.upper()}")
        console.print("────────────────────────────────────────────────")
        console.print()
        console.print("Feature coming soon.")
        
        action = prompt_action({"b": "Back", "x": "Exit"})
        if action == 'b': return
        elif action == 'x':
            if questionary.confirm("Exit? (y/n)").ask(): sys.exit(0)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()
    
    while True:
        print_main_menu()
        choice = console.input("Select [1-7]: [dim]→ [/dim]").strip()
        
        if choice == '1':
            submit_request_flow()
        elif choice == '2':
            pending_approvals_flow()
        elif choice == '3':
            audit_log_flow()
        elif choice == '4':
            placeholder_flow("🔍 Search by trace ID")
        elif choice == '5':
            placeholder_flow("📋 View policy rules")
        elif choice == '6':
            about_help_flow()
        elif choice == '7':
            if questionary.confirm("Exit? (y/n)").ask():
                sys.exit(0)
        else:
            console.print("Invalid selection. Please enter 1-7.")

if __name__ == "__main__":
    main()
