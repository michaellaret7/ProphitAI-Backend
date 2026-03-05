"""Option quote/snapshot tool — full details for a specific contract."""

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response


# ================================
# --> Helper funcs
# ================================

def _decode_display(osi_symbol: str) -> dict:
    """Decode OSI symbol into human-readable components."""
    from app.repositories.options import decode_osi
    root, expiration, opt_type, strike = decode_osi(osi_symbol)
    if root is None:
        return {}
    return {
        "root": root,
        "expiration": expiration,
        "type": opt_type,
        "strike": strike,
    }


# ================================
# --> Tools
# ================================

@agent_tool(name="get_option_quote")
def get_option_quote(osi_symbol: str) -> str:
    """
    Get a full snapshot (quote, last trade, and greeks) for a specific option contract.

    Provide the OSI symbol from get_option_contracts or get_options_chain.
    Returns bid/ask, last trade price/size, and greeks (delta, gamma, theta, vega, rho).

    Args:
        osi_symbol: OSI option symbol (e.g., 'AAPL260619C00200000')

    Returns:
        Snapshot with decoded contract info, quote, trade, and greeks

    Examples:
        get_option_quote(osi_symbol="AAPL260619C00200000")
        >>> {"success": True, "data": {"contract": {...}, "quote": {...}, "greeks": {...}}}
    """
    osi_symbol = osi_symbol.upper().strip()

    try:
        from app.repositories.options import get_options_repo
        repo = get_options_repo()

        snapshot = repo.get_option_snapshot(symbol=osi_symbol)

        # Reason: enrich with decoded contract info for readability
        contract_info = _decode_display(osi_symbol)
        if contract_info:
            snapshot["contract"] = contract_info

        return success_response(snapshot)
    except Exception as e:
        return error_response(f"Failed to fetch quote for {osi_symbol}: {e}")
