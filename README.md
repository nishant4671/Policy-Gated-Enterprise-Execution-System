# Policy-Gated Enterprise Execution System

**A safe, auditable architecture for human-in-the-loop autonomous task execution in enterprise environments.**

![Python](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-6%20passing-brightgreen)
![Status](https://img.shields.io/badge/status-research%20prototype-orange)

---

## Overview

Enterprise AI is shifting from answering questions to executing multi-step workflows across email, documents, CRM, HR, and finance systems. However, companies cannot safely deploy unrestricted autonomous agents because LLMs hallucinate, cannot be trusted as the final authority on permissions, and leave no reproducible audit trail.

The **Policy-Gated Enterprise Execution System** is a four-layer architecture that enables autonomous task execution while guaranteeing three properties:

1. **Policy enforcement** — every action is checked against deterministic rules before execution.
2. **Human approval** — high-risk actions pause and require explicit manager authorization.
3. **Complete auditability** — every thought, tool call, and decision is logged with a trace ID.

The LLM plans. The policy engine decides. The human approves. The audit ledger records.

---

## Key Results

Evaluated on 10 IT procurement scenarios:

| Metric | Naive Agent | Policy-Gated Agent | Improvement |
|--------|:-----------:|:------------------:|:-----------:|
| Correct verdicts | 3/10 | 8/10 | +167% |
| Unauthorized actions executed | 7 | 2 | −71% |
| High-risk purchases paused | 0/3 | 3/3 | +100% |
| Blocked red-team attempts | 0/4 | 2/4 | +50% |

Charts: [
esults/charts/](results/charts/)

---

## Architecture

Four independent layers. The LLM has no authority over security-critical decisions.

`	ext
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Streamlit UI (Human-in-the-Loop Gateway)           │
│ Employee console · Manager approvals · Audit viewer         │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: LangGraph Agent + LLM                              │
│ ReAct planner · Tool registry · Checkpointer · Groq/Gemini  │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: Policy Engine (Python + YAML)                      │
│ Deterministic rules · ALLOW / BLOCK / REQUIRE_APPROVAL      │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: Mock Enterprise Systems (FastAPI + SQLite)         │
│ HR · Finance · Vendor · Orders · Append-only audit ledger   │
└─────────────────────────────────────────────────────────────┘
`

**Safety guarantee:** Graph conditional edges route on state["policy_verdict"], a value set deterministically by check_policy(). The LLM cannot influence routing.

---

## How It Works

Example: an employee requests a premium laptop.

1. **Plan** — LLM identifies the request as a laptop purchase with premium preference.
2. **Fetch** — Agent retrieves employee role, department budget, and product catalog.
3. **Select** — Agent filters to approved vendors within budget.
4. **Policy Check** — Policy engine evaluates: cost > 1000 → **REQUIRE_HUMAN_APPROVAL**.
5. **Pause** — LangGraph checkpoints state and writes a PENDING row.
6. **Human Decision** — Manager approves or rejects via the dashboard.
7. **Execute** — Agent places order, sends confirmation, logs outcome.

---

## Policy Rules

Defined in [policy_engine/policy.yaml](policy_engine/policy.yaml):

| Rule | Condition | Verdict |
|------|-----------|---------|
| High Value Purchase | cost > 1000 | REQUIRE_HUMAN_APPROVAL |
| Unapproved Vendor | endor_approved == False | BLOCK |
| Intern Purchase Limit | 
ole == Intern and cost > 500 | BLOCK |
| Budget Exceeded | cost > remaining_budget | BLOCK |
| Forbidden Action | ction in [delete_employee, modify_salary, grant_admin] | BLOCK |

Default when no rule matches: ALLOW. On evaluation error: BLOCK (fail-closed).

---

## Getting Started

### Prerequisites

- Python 3.11+
- Groq API key ([free](https://console.groq.com/keys)) or Google AI Studio key ([free](https://aistudio.google.com/apikey))

### Installation

`ash
git clone https://github.com/nishant4671/policy-gated-execution.git
cd policy-gated-execution

python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

pip install -r requirements.txt
`

### Configuration

`ash
cp .env.example .env
`

Add to .env:

`env
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
`

Groq is primary. Gemini is automatic fallback if GROQ_API_KEY is unset.

### Initialize Database

`ash
python mock_systems/database.py
`

### Running the System

Two terminals required.

**Terminal 1 — Mock API:**

`ash
python mock_systems/api.py
`

**Terminal 2 — Dashboard:**

`ash
streamlit run ui/app.py
`

Opens at http://localhost:8501.

### Demo Walkthrough

| Step | Tab | Action | Expected |
|---|---|---|---|
| 1 | Submit Request | Buy a laptop, ID 101 | Verdict: ALLOW |
| 2 | Submit Request | Buy a premium laptop, ID 101 | awaiting_approval |
| 3 | Pending Approvals | Click Approve | Row moves to APPROVED |
| 4 | Submit Request | Buy a laptop, ID 103 | BLOCK (intern limit) |
| 5 | Audit Log | Refresh | All actions visible with trace IDs |

### Command-Line Usage

`ash
python agent/main.py "Buy a laptop" 101          # Normal
python agent/main.py "Buy a premium laptop" 101  # HITL trigger
python agent/main.py "Buy a laptop" 103          # Policy block
python agent/main.py "Buy a premium laptop" 101 --naive  # Baseline
`

## Project Structure

`	ext
policy-gated-execution/
├── mock_systems/          # Layer 1 — FastAPI + SQLite
│   ├── database.py
│   ├── api.py
│   └── enterprise.db
├── policy_engine/         # Layer 2 — Rules
│   ├── policy.yaml
│   ├── engine.py
│   └── test_policy.py
├── agent/                 # Layer 3 — LangGraph
│   ├── graph.py
│   ├── main.py
│   ├── state.py
│   └── tools.py
├── ui/                    # Layer 4 — Streamlit
│   ├── app.py
│   └── components.py
├── tests/                 # Benchmarks + eval
│   ├── test_cases.json
│   ├── run_eval.py
│   └── generate_charts.py
├── results/               # Evaluation outputs
│   ├── results.csv
│   └── charts/
├── report/                # Final write-up
│   └── final_report.md
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
`

## Testing

`ash
pytest tests/ -v
`

**Coverage:**
- policy_engine/test_policy.py — 10 unit tests (rule evaluation, boundaries, fail-closed)
- 	ests/test_tools.py — 6 tests (agent tool wrappers)

**Full benchmark:**

`ash
python tests/run_eval.py --mode safe
python tests/run_eval.py --mode naive
python tests/generate_charts.py
`

Evaluation is checkpointed — crashes resume from last successful case.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| Agent framework | LangGraph |
| LLM (primary) | Groq — openai/gpt-oss-120b |
| LLM (fallback) | Gemini 2.5 Flash |
| Mock APIs | FastAPI + Uvicorn |
| Database | SQLite (raw sqlite3) |
| UI | Streamlit |
| Charting | Matplotlib + Pandas |
| Testing | Pytest |

## Design Principles

1. **Separation of concerns** — planner, policy, UI, and ledger are independent.
2. **Deterministic safety** — security decisions are never delegated to the LLM.
3. **Human authority** — high-risk actions always require approval.
4. **Complete auditability** — every action logged with a trace ID.
5. **Fail-closed defaults** — malformed rules return BLOCK.
6. **Domain-agnostic** — swap tools and rules to target HR, invoicing, CRM.

## Limitations

1. **Out-of-scope intents bypass the policy engine.** Prompts like "delete employee 102" map to the closest available tool (buy a laptop) because the agent has no delete tool to reject. Policy scope equals toolset scope.
2. **SQLite write-locking** under concurrent load — production would use PostgreSQL.
3. **No structured output validation** — hallucinated product IDs cause downstream errors, not safety violations.
4. **Naive baseline is simulated** by disabling policy checks, not a separately built agent.

## Future Work

- Pre-planning intent classifier for out-of-scope rejection.
- PostgreSQL + PostgresSaver for persistent checkpoints.
- Pydantic structured output parsers.
- Generalization to HR, invoicing, CRM.
- Formal verification of graph reachability.
- Larger-scale evaluation on AgentBench/WebArena.

## References

1. Yao et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
2. Liu et al. (2023). AgentBench: Evaluating LLMs as Agents. arXiv:2308.03688.
3. Zhou et al. (2023). WebArena. arXiv:2307.13854.
4. Xie et al. (2024). OSWorld. arXiv:2404.07972.
5. Amershi et al. (2019). Guidelines for Human-AI Interaction. CHI.
6. Schick et al. (2023). Toolformer. NeurIPS.

## License

MIT — see LICENSE.

## Author

Nishant
Roll Number: 2414110427
Project Code: FAIR-AI-P03

## Acknowledgments

Built as part of the FAIR-AI Project-Based Learning track. Thanks to the project mentors and to the LangGraph and Groq teams for making this prototype possible.
