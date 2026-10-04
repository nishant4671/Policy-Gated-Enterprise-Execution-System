import json, time, subprocess, sys, os, argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.main import run

CHECKPOINT_FILE = "results/checkpoint.json"
RESULTS_FILE = "results/results.csv"
PER_CASE_TIMEOUT = 60

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            return json.load(open(CHECKPOINT_FILE))
        except Exception:
            return {"completed": []}
    return {"completed": []}

def save_checkpoint(cp):
    os.makedirs("results", exist_ok=True)
    json.dump(cp, open(CHECKPOINT_FILE, "w"), indent=2)

def run_with_timeout(request, employee_id, safe_mode, timeout=PER_CASE_TIMEOUT):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run, request, employee_id, safe_mode)
        try:
            return future.result(timeout=timeout)
        except FutureTimeout:
            print(f"    !! TIMEOUT after {timeout}s — skipping", flush=True)
            return {"status": "timeout", "policy_verdict": "TIMEOUT",
                    "policy_rule": "timeout", "final_result": "Timed out"}
        except Exception as e:
            print(f"    !! ERROR: {type(e).__name__}: {e}", flush=True)
            return {"status": "error", "policy_verdict": "ERROR",
                    "policy_rule": str(e), "final_result": str(e)}

def main(mode, limit=None):
    cases = json.load(open("tests/test_cases.json"))
    if limit:
        cases = cases[:limit]

    cp = load_checkpoint()
    print(f"[INIT] mode={mode}, cases={len(cases)}, already_done={len(cp['completed'])}", flush=True)

    api = subprocess.Popen([sys.executable, "mock_systems/api.py"])
    time.sleep(4)
    print("[INIT] Mock API started", flush=True)

    results = []
    try:
        for i, case in enumerate(cases, 1):
            key = f"{case['id']}_{mode}"
            if key in cp["completed"]:
                print(f"[{i}/{len(cases)}] {mode} case {case['id']} — SKIPPED (cached)", flush=True)
                continue

            print(f"\n[{i}/{len(cases)}] {mode} | case {case['id']} | '{case['prompt'][:50]}'", flush=True)
            safe_mode = (mode == "safe")

            t0 = time.time()
            res = run_with_timeout(case["prompt"], case["employee_id"], safe_mode)
            elapsed = time.time() - t0

            verdict = res.get("policy_verdict")
            status = res.get("status")
            print(f"    [{elapsed:.1f}s] verdict={verdict}, status={status}", flush=True)

            results.append({
                "case_id": case["id"],
                "category": case["category"],
                "prompt": case["prompt"],
                "employee_id": case["employee_id"],
                "expected_verdict": case["expected_verdict"],
                "mode": mode,
                "verdict": verdict,
                "status": status,
                "correct": (verdict == case["expected_verdict"]),
            })

            cp["completed"].append(key)
            save_checkpoint(cp)
            print(f"    [checkpoint] {len(cp['completed'])} total", flush=True)
    finally:
        api.terminate()
        print("[INIT] Mock API stopped", flush=True)

    if results:
        if os.path.exists(RESULTS_FILE):
            try:
                existing = pd.read_csv(RESULTS_FILE)
                new_df = pd.DataFrame(results)
                existing = existing.merge(
                    new_df[["case_id", "mode"]],
                    on=["case_id", "mode"],
                    how="left",
                    indicator=True
                ).query("_merge == 'left_only'").drop(columns=["_merge"])
                combined = pd.concat([existing, new_df], ignore_index=True)
            except Exception:
                combined = pd.DataFrame(results)
        else:
            combined = pd.DataFrame(results)
        os.makedirs("results", exist_ok=True)
        combined.to_csv(RESULTS_FILE, index=False)
        print(f"\n[SAVED] {len(combined)} total rows to {RESULTS_FILE}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="safe", choices=["safe", "naive"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(mode=args.mode, limit=args.limit)
