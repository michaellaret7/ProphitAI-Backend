from typing import Any
from prophitai_data.repositories.screener import screen_equities, screen_etfs
from prophitai_api.utils.response_envelope import ok_envelope


def run_equity_screener(**kwargs) -> dict[str, Any]:
    """
    Run equity screener and return JSON-serializable results.

    Args:
        **kwargs: Screener filters. Numeric ranges use [min, max] arrays
                  (e.g., market_cap=[1000000000, null] for min $1B).
                  Classification filters use string arrays
                  (e.g., sectors=['equity_sector_financials']).

    Returns:
        dict with 'results' (list of dicts) on success,
        or 'error' (str) on failure
    """
    # Convert lists to tuples for range parameters (API sends JSON arrays)
    converted_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list) and len(value) == 2:
            converted_kwargs[key] = tuple(value)
        else:
            converted_kwargs[key] = value

    results, error = screen_equities(**converted_kwargs)

    if error:
        return {"error": error}

    results = [result.model_dump() for result in results]

    return ok_envelope(
        message=f"Equity screener results for '{kwargs}' retrieved successfully",
        kind="screeners#equity",
        resource_id=kwargs,
        self_link=f"/api/screeners/equity?{kwargs}",
        counts={"totalItems": len(results) if results else 0, "currentItemCount": len(results) if results else 0},
        payload=results,
    )


def run_etf_screener(**kwargs) -> dict[str, Any]:
    """
    Run ETF screener and return JSON-serializable results.

    Args:
        **kwargs: Screener filters. Numeric ranges use [min, max] arrays
                  (e.g., market_cap=[1000000000, null] for min $1B).
                  Classification filters use string arrays
                  (e.g., industries=['equity_etfs']).

    Returns:
        dict with 'results' (list of dicts) on success,
        or 'error' (str) on failure
    """
    # Convert lists to tuples for range parameters (API sends JSON arrays)
    converted_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list) and len(value) == 2:
            converted_kwargs[key] = tuple(value)
        else:
            converted_kwargs[key] = value

    results, error = screen_etfs(**converted_kwargs)

    if error:
        return {"error": error}

    results = [result.model_dump() for result in results]

    return ok_envelope(
        message=f"ETF screener results for '{kwargs}' retrieved successfully",
        kind="screeners#etf",
        resource_id=kwargs,
        self_link=f"/api/screeners/etf?{kwargs}",
        counts={"totalItems": len(results) if results else 0, "currentItemCount": len(results) if results else 0},
        payload=results,
    )
