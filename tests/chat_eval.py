"""ChatAgent evaluation script.

Runs 10 diverse finance tasks through the ChatAgent, captures results,
grades outputs via LLM-as-judge, and prints a summary table.

Modes:
  python tests/chat_eval.py           # Run all 10 tasks → chat_eval_results.json
  python tests/chat_eval.py --verify  # Run subset (tasks 1, 3, 9) → chat_eval_verify.json
  python tests/chat_eval.py --grade   # Grade existing results JSON via LLM
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

from app.core.atlas.agents.chat_agent import ChatAgent
from app.core.atlas.models import PrintMode
from app.utils.choose_model_and_client import get_model_and_client

# ================================
# --> Test task definitions
# ================================

TEST_TASKS = [
    {
        "id": "single_ticker_overview",
        "prompt": "Give me a quick overview of AAPL - current price, P/E ratio, and recent performance",
        "difficulty": "simple",
    },
    {
        "id": "macro_concept",
        "prompt": "What is the current federal funds rate and how has it changed over the past year?",
        "difficulty": "simple",
    },
    {
        "id": "ticker_comparison",
        "prompt": "Compare NVDA and AMD on valuation, revenue growth, and analyst sentiment",
        "difficulty": "moderate",
    },
    {
        "id": "sector_analysis",
        "prompt": "Analyze the energy sector - what are the top performing energy stocks this year and why?",
        "difficulty": "moderate",
    },
    {
        "id": "macro_implications",
        "prompt": "How would a potential Fed rate cut impact REITs and utility stocks? Research current rate expectations and sector positioning",
        "difficulty": "moderate",
    },
    {
        "id": "stock_screening",
        "prompt": "Screen for large-cap tech stocks with P/E under 25, revenue growth above 15%, and positive analyst revisions",
        "difficulty": "moderate",
    },
    {
        "id": "portfolio_risk",
        "prompt": "Analyze the risk profile of an equal-weight portfolio of AAPL, MSFT, GOOGL, AMZN, META - include correlation, drawdown risk, and concentration concerns",
        "difficulty": "complex",
    },
    {
        "id": "earnings_deep_dive",
        "prompt": "Analyze NVDA's latest earnings report and call transcript. What did management say about data center demand, China exposure, and margin outlook?",
        "difficulty": "complex",
    },
    {
        "id": "investment_thesis",
        "prompt": "Build a bull and bear investment thesis for NVDA over the next 12 months. Include fundamental analysis, competitive positioning, earnings estimates, price targets, and key risks",
        "difficulty": "complex",
    },
    {
        "id": "multi_asset_allocation",
        "prompt": "I have $500K to allocate across US equities, international equities, bonds, and alternatives. Given the current macro environment, propose an allocation with specific ETF recommendations and justify each decision",
        "difficulty": "complex",
    },
]

RESULTS_PATH = Path(__file__).parent / "chat_eval_results.json"
VERIFY_PATH = Path(__file__).parent / "chat_eval_verify.json"

# Reason: subset of tasks for quick re-validation after prompt changes
VERIFY_TASK_IDS = {"single_ticker_overview", "ticker_comparison", "investment_thesis"}

# ================================
# --> Grading configuration
# ================================

GRADING_CRITERIA = [
    {"name": "accuracy", "weight": 0.25, "description": "Factual correctness, real data vs hallucination"},
    {"name": "relevance", "weight": 0.20, "description": "Answers the actual question, stays on topic"},
    {"name": "depth", "weight": 0.15, "description": "Multi-angle research thoroughness"},
    {"name": "tool_usage", "weight": 0.15, "description": "Right tools, appropriate number of calls"},
    {"name": "actionability", "weight": 0.15, "description": "Decision-useful output with specific recommendations"},
    {"name": "structure", "weight": 0.10, "description": "Organization, readability, formatting"},
]

GRADER_SYSTEM_PROMPT = """You are an expert evaluator of financial research AI assistants.
You will be given a user prompt and the agent's response to that prompt.
Grade the response on the following criteria, each scored 1-10:

{criteria_block}

Return ONLY a JSON object with this exact structure (no markdown, no extra text):
{{
  "accuracy": <int 1-10>,
  "relevance": <int 1-10>,
  "depth": <int 1-10>,
  "tool_usage": <int 1-10>,
  "actionability": <int 1-10>,
  "structure": <int 1-10>,
  "strengths": "<1-2 sentence summary of what the response did well>",
  "weaknesses": "<1-2 sentence summary of what could be improved>"
}}"""


def _build_criteria_block() -> str:
    """Build the criteria description block for the grader prompt."""
    lines = []
    for c in GRADING_CRITERIA:
        lines.append(f"- **{c['name']}** (weight {c['weight']}): {c['description']}")
    return "\n".join(lines)


# ================================
# --> Runner
# ================================


def run_single_task(task: dict) -> dict:
    """Run the ChatAgent on a single task and return results."""
    print(f"\n{'='*60}")
    print(f"  Running: {task['id']} [{task['difficulty']}]")
    print(f"  Prompt:  {task['prompt']}")
    print(f"{'='*60}")

    agent = ChatAgent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
    )

    start = time.time()
    response = agent.run(task["prompt"])
    elapsed = round(time.time() - start, 2)

    result = {
        "id": task["id"],
        "prompt": task["prompt"],
        "difficulty": task["difficulty"],
        "answer": response.answer,
        "tool_calls_made": response.tool_calls_made,
        "tool_call_count": len(response.tool_calls_made),
        "tokens_used": response.tokens_used,
        "iterations": response.iterations,
        "stop_reason": response.stop_reason,
        "elapsed_seconds": elapsed,
    }

    print(f"\n  Result: {len(response.tool_calls_made)} tool calls, "
          f"{response.iterations} iterations, {elapsed}s")
    print(f"  Tools used: {response.tool_calls_made}")
    print(f"  Answer preview: {response.answer[:200]}...")

    return result


def run_tasks(tasks: list, results_file: Path) -> None:
    """Run a list of tasks and save results to JSON."""
    results = []

    for task in tasks:
        try:
            result = run_single_task(task)
            results.append(result)
        except Exception as e:
            print(f"\n  ERROR on {task['id']}: {e}")
            results.append({
                "id": task["id"],
                "prompt": task["prompt"],
                "difficulty": task["difficulty"],
                "error": str(e),
            })

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    for r in results:
        if "error" in r:
            print(f"  {r['id']}: ERROR - {r['error']}")
        else:
            print(f"  {r['id']}: {r['tool_call_count']} tools, "
                  f"{r['iterations']} iters, {r['elapsed_seconds']}s")

    print(f"\nResults saved to {results_file}")


# ================================
# --> Grader
# ================================


def grade_single_result(result: dict, model_name: str, client) -> dict:
    """Grade a single result using LLM-as-judge."""
    if "error" in result:
        return {"error": result["error"]}

    criteria_block = _build_criteria_block()
    system = GRADER_SYSTEM_PROMPT.format(criteria_block=criteria_block)

    # Reason: include tool call info so grader can evaluate tool_usage criterion
    tool_info = (
        f"\n\nTool calls made ({result['tool_call_count']} total): "
        f"{', '.join(result['tool_calls_made'])}"
    )

    user_msg = (
        f"## User Prompt\n{result['prompt']}\n\n"
        f"## Difficulty Level\n{result['difficulty']}\n\n"
        f"## Agent Response\n{result['answer']}"
        f"{tool_info}"
    )

    response = client.chat.completions.create(
        model=model_name,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Reason: strip markdown code fences if the LLM wraps JSON in them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        grades = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  WARNING: Could not parse grader output for {result['id']}")
        print(f"  Raw output: {raw[:300]}")
        return {"error": "grader_parse_failure", "raw": raw}

    # Reason: compute weighted overall score
    overall = sum(
        grades.get(c["name"], 0) * c["weight"]
        for c in GRADING_CRITERIA
    )
    grades["overall"] = round(overall, 2)

    return grades


def grade_results(results_file: Path) -> None:
    """Grade all results in a JSON file and update it in place."""
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    model_name, client = get_model_and_client("anthropic", "claude-sonnet-4-6")

    print(f"\nGrading {len(results)} results with {model_name}...")

    for i, result in enumerate(results):
        task_id = result.get("id", f"task_{i}")
        print(f"  Grading: {task_id}...", end=" ", flush=True)

        grades = grade_single_result(result, model_name, client)
        result["grades"] = grades

        if "error" in grades:
            print(f"ERROR - {grades['error']}")
        else:
            print(f"overall={grades['overall']}")

    # Reason: save graded results back to the same file
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print_grade_table(results)
    print(f"\nGraded results saved to {results_file}")


def print_grade_table(results: list) -> None:
    """Print a formatted grade summary table."""
    print(f"\n{'='*85}")
    header = (
        f"{'Task':<28} {'Acc':>4} {'Dep':>4} {'Rel':>4} "
        f"{'Str':>4} {'Tool':>4} {'Act':>4} {'Overall':>8}"
    )
    print(header)
    print("-" * 85)

    totals = {c["name"]: [] for c in GRADING_CRITERIA}
    totals["overall"] = []

    for r in results:
        grades = r.get("grades", {})
        if "error" in grades:
            print(f"  {r['id']:<26} {'ERROR':>50}")
            continue

        acc = grades.get("accuracy", 0)
        dep = grades.get("depth", 0)
        rel = grades.get("relevance", 0)
        stru = grades.get("structure", 0)
        tool = grades.get("tool_usage", 0)
        act = grades.get("actionability", 0)
        overall = grades.get("overall", 0)

        print(
            f"  {r['id']:<26} {acc:>4} {dep:>4} {rel:>4} "
            f"{stru:>4} {tool:>4} {act:>4} {overall:>8.2f}"
        )

        totals["accuracy"].append(acc)
        totals["depth"].append(dep)
        totals["relevance"].append(rel)
        totals["structure"].append(stru)
        totals["tool_usage"].append(tool)
        totals["actionability"].append(act)
        totals["overall"].append(overall)

    print("-" * 85)

    # Reason: compute averages only from non-empty lists
    def avg(lst: list) -> float:
        return round(sum(lst) / len(lst), 1) if lst else 0.0

    print(
        f"  {'AVERAGE':<26} {avg(totals['accuracy']):>4} {avg(totals['depth']):>4} "
        f"{avg(totals['relevance']):>4} {avg(totals['structure']):>4} "
        f"{avg(totals['tool_usage']):>4} {avg(totals['actionability']):>4} "
        f"{avg(totals['overall']):>8.2f}"
    )
    print(f"{'='*85}")

    # Reason: print strengths/weaknesses summary for quick diagnosis
    print(f"\n{'='*60}")
    print("  STRENGTHS & WEAKNESSES")
    print(f"{'='*60}")
    for r in results:
        grades = r.get("grades", {})
        if "error" in grades:
            continue
        print(f"\n  [{r['id']}]")
        print(f"    + {grades.get('strengths', 'N/A')}")
        print(f"    - {grades.get('weaknesses', 'N/A')}")


# ================================
# --> Main
# ================================


def main():
    """Entry point. Supports --verify and --grade flags."""
    if "--grade" in sys.argv:
        # Reason: grade whichever results file exists, prefer verify if both flags given
        if "--verify" in sys.argv or VERIFY_PATH.exists() and not RESULTS_PATH.exists():
            target = VERIFY_PATH
        else:
            target = RESULTS_PATH

        if not target.exists():
            print(f"ERROR: {target} not found. Run eval first.")
            sys.exit(1)

        grade_results(target)
        return

    if "--verify" in sys.argv:
        tasks = [t for t in TEST_TASKS if t["id"] in VERIFY_TASK_IDS]
        run_tasks(tasks, VERIFY_PATH)
    else:
        run_tasks(TEST_TASKS, RESULTS_PATH)


if __name__ == "__main__":
    main()
