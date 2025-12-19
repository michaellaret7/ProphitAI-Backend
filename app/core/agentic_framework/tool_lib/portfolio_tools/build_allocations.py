from typing import List, Dict
from app.core.calculations.portfolio.allocator.allocate import run
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

# add proper llm error handling

def build_allocations(
    tickers: List[str], 
    equity_weight_target: float = 0.60, 
    bond_weight_target: float = 0.40
) -> Dict[str, float]:

    try:
        allocations = run(tickers, equity_weight_target, bond_weight_target)
        return success_response(allocations)
    except Exception as e:
        if not tickers:
            return error_response("Tickers list is empty")

        return error_response(f"Error building allocations: {e}")

