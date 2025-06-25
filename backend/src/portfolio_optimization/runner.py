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
from backend.src.repositories.portfolio.push_created_portfolio_repository import PushUserCreatedPortfolioRepository
from backend.src.data.user_information import get_user_information

def run_workflow(user_id: str, email: str) -> Dict[str, Any] | None:
    """
    Run phase-one → phase-two workflow and return recommendations JSON.
    All database operations are deferred until the end of a successful workflow.

    Args:
        user_id: The ID of the user for whom the workflow is run.
        email: The email of the user.
    """
    
    phase_one_data: Dict[str, Any] | None = None
    phase_two_recs: Dict[str, Any] | None = None

    try:
        print("🚀 Starting workflow ...")

        # ---------------- 1️⃣  Phase-one: Build draft portfolio -----------------
        print("\n 🏗️  Running Phase-One optimisation …")
        phase_one_data = optimize(user_id=user_id, email=email)
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
        
        portfolio_name = "sss_portfolio"
        print(f"\n💾 All phases successful. Preparing to store data for portfolio: {portfolio_name} ...")

        # Initialize the repository
        repo = PushUserCreatedPortfolioRepository()

        # Create portfolio and get UUID
        print(f"   Creating portfolio '{portfolio_name}'...")
        current_portfolio_id = repo.store_portfolio(
            portfolio_name=portfolio_name,
            user_id=user_id,
            email=email
        )
        
        if not current_portfolio_id:
            print("Failed to create portfolio. Aborting workflow.")
            return None
        
        print(f"     Portfolio UUID {current_portfolio_id} created for '{portfolio_name}'.")

        # Store sector allocations
        print(f"   Storing sector allocations for '{portfolio_name}'...")
        sector_success = repo.store_sector_allocations(
            portfolio=phase_one_data,
            portfolio_id=current_portfolio_id,
            portfolio_name=portfolio_name,
            user_id=user_id,
            email=email
        )
        
        if sector_success:
            print("     Sector allocations stored successfully.")
        else:
            print("     Failed to store sector allocations.")

        # Store final portfolio recommendations
        print(f"   Storing final portfolio recommendations for '{portfolio_name}'...")
        repo.store_final_portfolio(
            portfolio=phase_two_recs,
            portfolio_id=current_portfolio_id,
            portfolio_name=portfolio_name,
            user_id=user_id,
            email=email
        )
        print("     Final portfolio recommendations stored.")

        # Store portfolio thesis if available
        if phase_one_data.get("portfolio_thesis"):
            print(f"   Storing portfolio thesis for '{portfolio_name}'...")
            thesis_success = repo.store_portfolio_thesis(
                portfolio_id=current_portfolio_id,
                portfolio_name=portfolio_name,
                thesis=phase_one_data["portfolio_thesis"],
                user_id=user_id,
                email=email
            )
            
            if thesis_success:
                print("     Portfolio thesis stored successfully.")
            else:
                print("     Failed to store portfolio thesis.")

        # Store user information
        print(f"   Storing user information for portfolio '{portfolio_name}'...")
        user_profile = get_user_information()
        user_info_success = repo.store_user_information(
            portfolio_id=current_portfolio_id,
            portfolio_name=portfolio_name,
            user_id=user_id,
            email=email,
            user_profile=user_profile
        )
        
        if user_info_success:
            print("     User information stored successfully.")
        else:
            print("     Failed to store user information.")
        
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
    # Mock user data for direct script execution
    test_user_id = "user_01JXG39MMAVW1P3XVGX7YHN2DT"
    test_email = "michael@laret.com"
    final_recommendations = run_workflow(user_id=test_user_id, email=test_email)
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
