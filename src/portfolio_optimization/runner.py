"""portfolio_optimization.runner
=================================
CLI / module entry-point that executes the full portfolio-optimisation
workflow:

phase-one  → draft portfolio allocations
phase-two  → pick tickers + generate recommendations

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
from time import perf_counter

from . import optimize, run_phase_two
from src.data.final_portfolio_data import (
    store_portfolio_sector_allocations,
    store_final_portfolio,
    store_user_information
)


def run_workflow() -> Dict[str, Any] | None:  # noqa: D401
    """Run phase-one → phase-two workflow and return recommendations JSON."""

    try:
        # ---------------- 1️⃣  Phase-one: Build draft portfolio -----------------
        print("\n🚀  Running Phase-One optimisation …\n")
        portfolio_json = optimize()
        if not portfolio_json or "portfolio" not in portfolio_json:
            print("Phase-One did not return a valid portfolio JSON.")
            return None
            
        # Store portfolio sector allocations in the database
        schema_name = store_portfolio_sector_allocations(portfolio_json)
        print(f"\n💾  Portfolio sector allocations stored in schema '{schema_name}'")

        # ---------------- 2️⃣  Phase-two: Select tickers -----------------------
        print("\n📈  Running Phase-Two ticker selection …\n")
        recs = run_phase_two(portfolio_json)
        if not recs:
            print("Phase-Two failed to generate ticker data.")
            return None
            
        # Store final portfolio recommendations in the database
        schema_name = store_final_portfolio(recs)
        print(f"\n💾  Final portfolio recommendations stored in schema '{schema_name}'")
        
        # Store user information in the database
        schema_name = store_user_information()
        print(f"\n👤  User information stored in schema '{schema_name}'")

        return recs

    except KeyboardInterrupt:
        print("Workflow interrupted by user.")
        return None
    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    start_time = perf_counter()
    result = run_workflow()
    elapsed = perf_counter() - start_time

    # Report execution time

    if result is not None:
        # Print nicely-formatted JSON to stdout
        print("🎯  Final Recommendations:\n")
        print(json.dumps(result, indent=2))
    else:
        sys.exit(1) 

    print(f"\n ⏱️  Workflow executed in {elapsed:.2f} seconds.\n")
