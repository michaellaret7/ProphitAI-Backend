"""PlannerAgent evaluation script.

Runs 8 diverse tasks through the PlannerAgent, captures raw answers and parsed
Plan objects, saves results to JSON, and prints a summary.
"""

import json
import os
import sys
import time
from pathlib import Path

# Reason: Windows console defaults to charmap which can't handle unicode arrows in printer
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.atlas.agents.planner_agent import PlannerAgent
from app.core.atlas.models import PrintMode

# ================================
# --> Test task definitions
# ================================

TEST_TASKS = [
    {
        "id": "simple_comparison",
        "prompt": "Analyze AAPL and MSFT and compare their performance and valuation",
    },
    {
        "id": "portfolio_construction",
        "prompt": "Build a 10-stock long-only portfolio focused on AI/semiconductor companies with risk constraints",
    },
    {
        "id": "macro_research",
        "prompt": "Analyze the current macro environment and its implications for equity markets",
    },
    {
        "id": "single_stock_deep_dive",
        "prompt": "Do a comprehensive analysis of NVDA including fundamentals, technicals, risk, and earnings",
    },
    {
        "id": "sector_analysis",
        "prompt": "Compare the healthcare and technology sectors — identify which offers better risk-adjusted returns",
    },
    {
        "id": "screening",
        "prompt": "Find undervalued small-cap stocks with strong momentum and low debt",
    },
    {
        "id": "risk_analysis",
        "prompt": "Evaluate the downside risk of a portfolio holding AAPL, GOOGL, AMZN, MSFT, META equally weighted",
    },
    {
        "id": "multi_asset",
        "prompt": "Research and compare gold, treasury bonds, and the S&P 500 as portfolio diversifiers",
    },
]

RESULTS_PATH = Path(__file__).parent / "planner_eval_results.json"

# Reason: subset of tasks for quick re-validation after prompt changes
VERIFY_TASK_IDS = {"simple_comparison", "portfolio_construction", "risk_analysis"}


def run_single_task(task: dict) -> dict:
    """Run the PlannerAgent on a single task and return results."""
    print(f"\n{'='*60}")
    print(f"  Running: {task['id']}")
    print(f"  Prompt:  {task['prompt']}")
    print(f"{'='*60}")

    planner = PlannerAgent(
        task=task["prompt"],
        provider="anthropic",
        model="claude-opus-4-6",
        print_mode=PrintMode.PRODUCTION,
    )

    start = time.time()
    plan = planner.run()
    elapsed = round(time.time() - start, 2)

    # Reason: extract the raw answer from the execution loop's last response
    raw_answer = planner.messages[-1].get("content", "") if planner.messages else ""

    result = {
        "id": task["id"],
        "prompt": task["prompt"],
        "elapsed_seconds": elapsed,
        "task_count": len(plan.tasks),
        "tasks": [t.model_dump() for t in plan.tasks],
        "raw_answer": raw_answer,
    }

    # Print summary
    print(f"\n  Result: {len(plan.tasks)} tasks in {elapsed}s")
    for t in plan.tasks:
        print(f"    [step {t.step} | {t.id}] {t.description}")

    return result


def main():
    """Run all test tasks and save results.

    Pass --verify flag to only run the verification subset.
    """
    verify_only = "--verify" in sys.argv
    tasks_to_run = [t for t in TEST_TASKS if t["id"] in VERIFY_TASK_IDS] if verify_only else TEST_TASKS
    results_file = Path(__file__).parent / ("planner_eval_verify.json" if verify_only else "planner_eval_results.json")
    results = []

    for task in tasks_to_run:
        try:
            result = run_single_task(task)
            results.append(result)
        except Exception as e:
            print(f"\n  ERROR on {task['id']}: {e}")
            results.append({
                "id": task["id"],
                "prompt": task["prompt"],
                "error": str(e),
            })

    # Save results
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    for r in results:
        if "error" in r:
            print(f"  {r['id']}: ERROR - {r['error']}")
        else:
            task_count = r["task_count"]
            # Reason: count distinct step numbers for parallelism analysis
            step_ids = [t["id"] for t in r["tasks"]]
            print(f"  {r['id']}: {task_count} tasks, steps={step_ids}, {r['elapsed_seconds']}s")

    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
