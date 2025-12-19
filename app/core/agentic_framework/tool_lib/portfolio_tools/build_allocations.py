from typing import List, Dict, Literal
from app.core.calculations.portfolio.allocator.allocate import run
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

# add proper llm error handling

def build_allocations(
    tickers: List[str], 
    equity_weight_target: float = 0.60, 
    bond_weight_target: float = 0.40,
    strategy: Literal["max_sharpe", "min_vol", "max_utility", "efficient_risk"] = "max_sharpe",
    initial_portfolio_value: float = 100_000,
) -> Dict[str, float]:

    if not tickers:
        return error_response("Tickers list is empty")

    try:
        allocations = run(
            tickers=tickers,
            equity_weight_target=equity_weight_target,
            bond_weight_target=bond_weight_target,
            initial_portfolio_value=initial_portfolio_value,
            strategy=strategy,
        )
        return success_response(allocations)
    except Exception as e:
        return error_response(f"Error building allocations: {e}")

if __name__ == "__main__":
    final_output = build_allocations(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ", "UNH", "PG", "AGG", "BND", "TLT", "IEF", "LQD", "VCIT"], 
        equity_weight_target=0.60, 
        bond_weight_target=0.40, 
        strategy="min_vol",
        initial_portfolio_value=100_000,
    )

    print(final_output)