"""Standalone validator test against an already-built strategy branch.

Spins up a sandbox, clones the Strategies repo on an existing
``strategy/{strategy_id}`` branch (all of indicators/signals/strategy/wiring
already built and committed), then runs the ValidatorAgent against it.

Usage (from repo root with .venv activated):
    python projects/fund/tests/test_validator_standalone.py

Change STRATEGY_ID to pick a different built strategy branch.
"""

from prophitai_atlas.models.print_mode import PrintMode
from prophitai_fund.validation.agent import ValidatorAgent
from prophitai_tools.sandbox.client import create_sandbox
from prophitai_tools.sandbox.lifecycle import close_sandbox, setup_repo


STRATEGY_ID = "working_capital_velocity_and_cash_conversion_cycle_improvement"
MODEL = "anthropic/claude-sonnet-4.6"


def main() -> None:
    sandbox_id, sandbox = create_sandbox(timeout=3600)

    try:
        setup_repo(sandbox, STRATEGY_ID)

        validator = ValidatorAgent(
            model=MODEL,
            sandbox_id=sandbox_id,
            print_mode=PrintMode.VERBOSE,
        )

        response = validator.run(strategy_id=STRATEGY_ID)

        verdict = response.parsed_output

        print("\n=== VALIDATION VERDICT ===")

        if verdict:
            print(f"Strategy:  {verdict.strategy_name}")
            print(f"Verdict:   {verdict.verdict}")
            print(f"Best run:  #{verdict.best_run_index}")
            print(f"Runs:      {len(verdict.runs)}/12")

            if 0 <= verdict.best_run_index < len(verdict.runs):
                best = verdict.runs[verdict.best_run_index]
                print(f"Sharpe:    {best.sharpe:.3f}")
                print(f"Metrics:   {best.metrics}")

            print(f"\nUniverse ({verdict.universe.asset_class}, {len(verdict.universe.tickers)} tickers):")
            print(f"  {verdict.universe.tickers}")
        else:
            print("No parsed verdict — raw answer:")
            print(response.answer)

    finally:
        close_sandbox(sandbox_id)


if __name__ == "__main__":
    main()
