import pandas as pd
import matplotlib.pyplot as plt
import os

df = pd.read_csv("results/results.csv")
os.makedirs("results/charts", exist_ok=True)

safe_df = df[df["mode"] == "safe"]
naive_df = df[df["mode"] == "naive"]

safe_correct = int(safe_df["correct"].sum())
naive_correct = int(naive_df["correct"].sum())
total_safe = len(safe_df)
total_naive = len(naive_df)

naive_unauth = len(naive_df[(naive_df["verdict"] == "ALLOW") & (naive_df["expected_verdict"] != "ALLOW")])
safe_unauth = len(safe_df[(safe_df["verdict"] == "ALLOW") & (safe_df["expected_verdict"] != "ALLOW")])

print("=== FINAL SUMMARY ===")
print(f"Safe Agent correct:    {safe_correct}/{total_safe}")
print(f"Naive Agent correct:   {naive_correct}/{total_naive}")
print(f"Safe unauthorized:     {safe_unauth}")
print(f"Naive unauthorized:    {naive_unauth}")

plt.figure(figsize=(6,4))
plt.bar(["Naive", "Safe"], [naive_unauth, safe_unauth], color=["#d9534f", "#5cb85c"])
plt.ylabel("Unauthorized Actions")
plt.title("Unauthorized Actions: Naive vs Safe")
plt.tight_layout()
plt.savefig("results/charts/unauthorized_actions.png", dpi=100)
plt.close()

plt.figure(figsize=(6,4))
plt.bar(["Naive", "Safe"],
        [naive_correct/max(total_naive,1)*100, safe_correct/max(total_safe,1)*100],
        color=["#d9534f", "#5cb85c"])
plt.ylabel("Correct Verdict Rate (%)")
plt.title("Task Correctness: Naive vs Safe")
plt.tight_layout()
plt.savefig("results/charts/task_completion.png", dpi=100)
plt.close()

plt.figure(figsize=(8,4))
verdicts = ["ALLOW", "REQUIRE_HUMAN_APPROVAL", "BLOCK"]
safe_counts = [len(safe_df[safe_df["verdict"] == v]) for v in verdicts]
naive_counts = [len(naive_df[naive_df["verdict"] == v]) for v in verdicts]
x = range(len(verdicts))
plt.bar([i - 0.2 for i in x], naive_counts, width=0.4, label="Naive", color="#d9534f")
plt.bar([i + 0.2 for i in x], safe_counts, width=0.4, label="Safe", color="#5cb85c")
plt.xticks(x, verdicts)
plt.ylabel("Count")
plt.title("Verdict Distribution")
plt.legend()
plt.tight_layout()
plt.savefig("results/charts/verdict_distribution.png", dpi=100)
plt.close()

print("Charts saved to results/charts/")
