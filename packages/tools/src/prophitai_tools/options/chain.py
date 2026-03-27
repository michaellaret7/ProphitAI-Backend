"""Options chain tool — full chain with quotes and greeks."""

from typing import Annotated, Literal, Optional

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Helper funcs
# ================================

def _empty_chain_hint(
    underlying: str,
    expiration: Optional[str],
    contract_type: Optional[str],
    min_strike: Optional[float],
    max_strike: Optional[float],
    min_bid: Optional[float],
) -> str:
    """Build a short diagnostic hint when the chain comes back empty."""
    if min_strike is not None and max_strike is not None and min_strike > max_strike:
        return f"min_strike ({min_strike}) > max_strike ({max_strike}) — range is inverted, swap the values."

    active_filters = []
    if expiration:
        active_filters.append(f"expiration={expiration}")
    if contract_type:
        active_filters.append(f"contract_type={contract_type}")
    if min_strike is not None:
        active_filters.append(f"min_strike={min_strike}")
    if max_strike is not None:
        active_filters.append(f"max_strike={max_strike}")
    if min_bid is not None:
        active_filters.append(f"min_bid={min_bid}")

    if active_filters:
        return (
            f"No contracts matched filters: {', '.join(active_filters)}. "
            "Try widening the strike range, removing min_bid, or checking the expiration date."
        )
    return f"No options data found for {underlying}. Verify the ticker has listed options."


# ================================
# --> Tools
# ================================

@agent_tool(name="get_options_chain", category="options")
def get_options_chain(
    underlying: str,
    expiration: Optional[str] = None,
    contract_type: Optional[Literal["call", "put"]] = None,
    min_strike: Optional[float] = None,
    max_strike: Optional[float] = None,
    min_bid: Optional[float] = None,
    limit: Annotated[int, Param(min_val=1, max_val=200)] = 50,
) -> str:
    """
    Fetch the options chain with quotes and greeks for an underlying.

    Returns chain rows with symbol, strike, type, bid/ask/mid, last price,
    and greeks (delta, gamma, theta, vega, IV). Rows are sorted by strike
    ascending, then type (call before put).

    Args:
        underlying: Underlying ticker symbol (e.g., 'AAPL', 'SPY')
        expiration: Filter to a specific expiration date (YYYY-MM-DD)
        contract_type: Filter to 'call' or 'put' only. None returns both.
        min_strike: Minimum strike price (inclusive). None = no lower bound.
        max_strike: Maximum strike price (inclusive). None = no upper bound.
        min_bid: Minimum bid price filter. None = no bid filtering (includes zero-bid).
            Pass 0.01 to exclude illiquid zero-bid contracts.
        limit: Maximum number of chain rows to return (1-200, default 50)

    Returns:
        List of chain rows with symbol, strike, type, bid, ask, mid, last, and greeks

    Examples:
        get_options_chain(underlying="SPY", expiration="2026-03-06", limit=20)
        get_options_chain(underlying="SPY", contract_type="put", max_strike=650, limit=10)
        get_options_chain(underlying="SPY", min_bid=0.01, limit=20)
        get_options_chain(underlying="SPY", min_strike=660, max_strike=680, limit=50)
    """
    underlying = underlying.upper().strip()
    if not underlying:
        return error_response("underlying symbol is required")

    try:
        from prophitai_data.clients.options import get_options_repo
        repo = get_options_repo()

        rows = repo.get_options_chain(
            underlying=underlying,
            expiration=expiration,
            limit=None,
            return_df=False,
        )

        if contract_type:
            rows = [r for r in rows if r.get("type") == contract_type]

        if min_strike is not None:
            rows = [r for r in rows if r.get("strike") is not None and r["strike"] >= min_strike]

        if max_strike is not None:
            rows = [r for r in rows if r.get("strike") is not None and r["strike"] <= max_strike]

        if min_bid is not None:
            rows = [r for r in rows if r.get("bid") is not None and r["bid"] >= min_bid]

        # Reason: strike-ascending, call before put gives a natural, predictable chain order
        rows.sort(key=lambda r: (r.get("strike", 0), r.get("type", "")))

        rows = rows[:limit]

        result = {
            "underlying": underlying,
            "count": len(rows),
            "chain": rows,
        }

        # Reason: when no rows survive filtering, add a hint so the agent
        # doesn't waste an iteration guessing why
        if len(rows) == 0:
            result["note"] = _empty_chain_hint(
                underlying, expiration, contract_type,
                min_strike, max_strike, min_bid,
            )

        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to fetch options chain for {underlying}: {e}")
