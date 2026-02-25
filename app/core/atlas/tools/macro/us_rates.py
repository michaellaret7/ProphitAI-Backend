"""US Treasury rates tool for macro analysis.

Fetches up to 60 days of daily yield curve data for US government bonds
across 12 maturities (1-month through 30-year).
"""

from typing import Annotated, Optional
from datetime import timedelta

import pandas as pd

from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.responses import success_response, error_response
from app.repositories.macro.rates import get_government_bond_rates
from app.utils.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

MATURITY_COLUMNS = ["m1", "m2", "m3", "m6", "y1", "y2", "y3", "y5", "y7", "y10", "y20", "y30"]


# ================================
# --> Tools
# ================================

@agent_tool(name="us_treasury_rates")
def us_treasury_rates(
    maturities: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": (
                "Maturities to return. If omitted, returns all 12.\n"
                "Valid: m1 (1-month), m2 (2-month), m3 (3-month), m6 (6-month), "
                "y1 (1-year), y2 (2-year), y3 (3-year), y5 (5-year), y7 (7-year), "
                "y10 (10-year), y20 (20-year), y30 (30-year)"
            ),
            "items": {"type": "string", "enum": MATURITY_COLUMNS},
            "default": None,
        }),
    ] = None,
    days_back: Annotated[int, Param(min_val=1, max_val=60)] = 30,
) -> str:
    """Fetch recent daily US Treasury yield curve data.

Returns daily rates for the requested maturities over the specified lookback period.

**Yield Curve Maturities (12 total):**
- Short-term: m1 (1-month), m2 (2-month), m3 (3-month), m6 (6-month)
- Medium-term: y1 (1-year), y2 (2-year), y3 (3-year), y5 (5-year), y7 (7-year)
- Long-term: y10 (10-year), y20 (20-year), y30 (30-year)

**Use Cases:**
- 2s10s spread: maturities=['y2', 'y10']
- Full yield curve snapshot: maturities=None
- Fed rate expectations: maturities=['m1', 'm3', 'y1', 'y2']
- Long-end only: maturities=['y10', 'y20', 'y30']

    Args:
        maturities: Maturity columns to return (default: all 12)
        days_back: Number of calendar days of history (default: 30, max: 60)

    Examples:
        us_treasury_rates(maturities=['y2', 'y10'])
        us_treasury_rates(maturities=['y10', 'y30'], days_back=60)
        us_treasury_rates()
    """
    try:
        target_maturities = maturities if maturities is not None else MATURITY_COLUMNS

        # Reason: validate maturity names against known columns
        invalid = [m for m in target_maturities if m not in MATURITY_COLUMNS]
        if invalid:
            return error_response(f"Invalid maturities: {invalid}. Valid: {MATURITY_COLUMNS}")

        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=days_back)

        df = get_government_bond_rates(country="USA", start_date=start_date, end_date=end_date)
        if df.empty:
            return success_response("No US Treasury rate data available for the specified date range.")

        # Reason: drop country column — always USA
        if "country" in df.columns:
            df = df.drop(columns=["country"])

        # Reason: keep only requested maturities + date
        df = df[["date"] + [m for m in target_maturities if m in df.columns]]

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Reason: drop maturities that have no data in the range (e.g. m2 pre-2018)
        df = df.dropna(axis=1, how="all")

        # Reason: drop rows with no rate data at all
        rate_cols = [c for c in df.columns if c != "date"]
        df = df.dropna(how="all", subset=rate_cols)

        for c in rate_cols:
            if c in df.columns:
                df[c] = df[c].round(3)

        df["date"] = df["date"].astype(str)
        return success_response(df.to_dict(orient="records"))

    except Exception as e:
        return error_response(f"Failed to fetch US Treasury rates: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(us_treasury_rates(maturities=["y2", "y10"], days_back=14))
