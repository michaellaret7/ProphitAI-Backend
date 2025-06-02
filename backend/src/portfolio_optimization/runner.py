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
from time import perf_counter, strftime
import uuid
import logging

# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from . import optimize, run_phase_two
from backend.src.data.final_portfolio_data import (
    store_portfolio_sector_allocations,
    store_final_portfolio,
    store_user_information
)

def run_workflow() -> Dict[str, Any] | None:
    """Run phase-one → phase-two workflow and return recommendations JSON.
    All database operations are deferred until the end of a successful workflow.
    """
    
    phase_one_data: Dict[str, Any] | None = None
    phase_two_recs: Dict[str, Any] | None = None
    # user_profile_data: Dict[str, Any] | None = None # User data fetched by store_user_information

    try:
        print("🚀 Starting workflow ...")

        # ---------------- 1️⃣  Phase-one: Build draft portfolio -----------------
        print("\n🏗️  Running Phase-One optimisation …")
        phase_one_data = optimize()
        if not phase_one_data or "portfolio" not in phase_one_data:
            print("Phase-One did not return a valid portfolio JSON. Aborting database operations.")
            return None
        print("   Phase-One optimisation completed.")

        # ---------------- 2️⃣  Phase-two: Select tickers -----------------------
        print("\n📈  Running Phase-Two ticker selection …")
        # Phase-two uses the sector allocation data (phase_one_data) as input
        phase_two_recs = run_phase_two(phase_one_data)
        if not phase_two_recs:
            print("Phase-Two failed to generate ticker data. Aborting database operations.")
            return None
        print("   Phase-Two ticker selection completed.")

        # ---------------- 3️⃣ All data collected, proceed to store ------------- 
        # If we reach here, both phases were successful.
        
        # portfolio_name = f"prophitai_run_{strftime('%Y%m%d_%H%M%S')}"
        portfolio_name = "techPEportfoliogpt4_1"
        print(f"\n💾 All phases successful. Preparing to store data for portfolio: {portfolio_name} ...")

        # Fetch user information just before storing if it's a separate call.
        # For now, store_user_information handles its own data fetching.
        # user_profile_data = get_user_information() 
        # if not user_profile_data:
        #     print("Failed to fetch user profile data. Aborting database operations.")
        #     return None

        print(f"   Storing sector allocations and thesis for '{portfolio_name}'...")
        current_portfolio_id: uuid.UUID = store_portfolio_sector_allocations(phase_one_data, portfolio_name)
        print(f"     Portfolio UUID {current_portfolio_id} created/retrieved for '{portfolio_name}'.")

        print(f"   Storing final portfolio recommendations for '{portfolio_name}' (UUID: {current_portfolio_id})...")
        store_final_portfolio(phase_two_recs, portfolio_id=current_portfolio_id, portfolio_name=portfolio_name)
        print(f"     Final portfolio recommendations stored.")
        
        print(f"   Storing user information for portfolio '{portfolio_name}' (UUID: {current_portfolio_id})...")
        store_user_information(portfolio_id=current_portfolio_id, portfolio_name=portfolio_name)
        print(f"     User information stored.")
        
        print("\n✅ All data successfully stored in the database.")
        return phase_two_recs # Return the final recommendations

    except KeyboardInterrupt:
        print("\n🛑 Workflow interrupted by user. No data will be stored.")
        return None
    except Exception as e: # Catching specific exceptions might be better
        print(f"\n❌ An error occurred during the workflow: {e}")
        traceback.print_exc()
        print("   No data will be stored due to the error.")
        return None


if __name__ == "__main__":
    start_time = perf_counter()
    final_recommendations = run_workflow()
    elapsed = perf_counter() - start_time

    if final_recommendations is not None:
        print("\n🎯  Final Recommendations (from workflow output):\n")
        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                return json.JSONEncoder.default(self, obj)
        print(json.dumps(final_recommendations, indent=2, cls=UUIDEncoder))
    else:
        print("\n ⚠️ Workflow did not complete successfully or was interrupted. No final recommendations to display from output.")
        # sys.exit(1) # Consider if exiting with error code is always desired here

    logger.info(f"Workflow executed in {elapsed:.2f} seconds.")
