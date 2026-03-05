"""Option contract discovery tool."""

from typing import Annotated, Literal, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response


# ================================
# --> Tools
# ================================

@agent_tool(name="get_option_contracts")
def get_option_contracts(
    underlying: str,
    expiration: Optional[str] = None,
    contract_type: Optional[Literal["call", "put"]] = None,
    min_strike: Optional[float] = None,
    max_strike: Optional[float] = None,
    limit: Annotated[int, Param(min_val=1, max_val=200)] = 50,
) -> str:
    """
    Discover available option contracts (OSI symbols) for an underlying.

    Use this to find specific contracts by expiration, type, and strike range.
    Returns OSI symbols that can be passed to get_option_quote or get_option_price_history.

    Args:
        underlying: Underlying ticker symbol (e.g., 'AAPL', 'SPY')
        expiration: Filter to a specific expiration date (YYYY-MM-DD)
        contract_type: Filter by 'call' or 'put'
        min_strike: Minimum strike price filter
        max_strike: Maximum strike price filter
        limit: Maximum number of contracts to return

    Returns:
        List of OSI option symbols (e.g., 'AAPL260320C00200000')

    Examples:
        get_option_contracts(underlying="AAPL", expiration="2026-06-19", contract_type="call", min_strike=190, max_strike=210)
        >>> {"success": True, "data": {"underlying": "AAPL", "contracts": ["AAPL260619C00190000", ...]}}
    """
    underlying = underlying.upper().strip()
    if not underlying:
        return error_response("underlying symbol is required")

    try:
        from app.repositories.options import get_options_repo
        repo = get_options_repo()

        # Reason: build strike_range tuple only if both or either bound provided
        strike_range = None
        if min_strike is not None or max_strike is not None:
            strike_range = (
                min_strike if min_strike is not None else 0.0,
                max_strike if max_strike is not None else 999999.0,
            )

        contracts = repo.get_available_contracts(
            underlying=underlying,
            expiration=expiration,
            contract_type=contract_type,
            strike_range=strike_range,
            limit=limit,
        )

        return success_response({
            "underlying": underlying,
            "count": len(contracts),
            "contracts": contracts,
        })
    except Exception as e:
        return error_response(f"Failed to fetch contracts for {underlying}: {e}")
