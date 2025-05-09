"""portfolio_optimization.runner
=================================
CLI / module entry-point that executes the full portfolio-optimisation
workflow:

phase-one  → draft portfolio allocations
phase-two  → pick tickers + generate fundamental reports
combine recommendations → print / return JSON

Run directly:
    python -m src.portfolio_optimization.runner
or
    python src/portfolio_optimization/runner.py

The helper will gracefully handle errors at each stage so a failure in the
LLM call does not crash the CLI.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict

from . import optimize, pick_top_tickers, recommend


def run_workflow() -> Dict[str, Any] | None:  # noqa: D401
    """Run phase-one → phase-two workflow and return recommendations JSON."""

    try:
        # ---------------- 1️⃣  Phase-one: Build draft portfolio -----------------
        print("\n🚀  Running Phase-One optimisation …\n")
        portfolio_json = optimize()
        if not portfolio_json or "portfolio" not in portfolio_json:
            print("Phase-One did not return a valid portfolio JSON.")
            return None

        # ---------------- 2️⃣  Phase-two: Select tickers -----------------------
        print("\n📈  Running Phase-Two ticker selection …\n")
        tickers_data = pick_top_tickers(portfolio_json)
        if not tickers_data:
            print("Phase-Two failed to generate ticker data.")
            return None

        # ---------------- 3️⃣  Recommendations --------------------------------
        print("\n🧠  Generating final recommendations …\n")
        recs_json_str = recommend(tickers_data)
        if recs_json_str is None:
            print("Recommendation step returned no data.")
            return None

        try:
            recs = json.loads(recs_json_str)
        except json.JSONDecodeError:
            # If the string is not valid JSON, return raw string under key
            recs = {"raw_response": recs_json_str}

        return recs

    except KeyboardInterrupt:
        print("Workflow interrupted by user.")
        return None
    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = run_workflow()
    if result is not None:
        # Print nicely-formatted JSON to stdout
        print("\n🎯  Final Recommendations:\n")
        print(json.dumps(result, indent=2))
    else:
        sys.exit(1) 