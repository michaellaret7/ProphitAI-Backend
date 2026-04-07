"""Commodity price data tool for macro analysis.

Fetches up to 60 days of daily OHLCV data for 16 major commodities across
precious metals, energy, industrial metals, agriculture, and volatility.
"""

from typing import Annotated, Optional
from datetime import timedelta

import pandas as pd

from prophitai_atlas.tools.decorator import agent_tool, Param, Schema
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.repositories.macro import get_commodity_prices
from prophitai_shared.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

COMMODITY_SYMBOLS = [
    "GCUSD",   # Gold
    "SIUSD",   # Silver
    "PLUSD",   # Platinum
    "PAUSD",   # Palladium
    "CLUSD",   # Crude Oil WTI
    "BRUSD",   # Brent Crude Oil
    "NGUSD",   # Natural Gas
    "HGUSD",   # Copper
    "ZSUSD",   # Sugar
    "CCUSD",   # Cocoa
    "CTUSD",   # Cotton
    "KCUSD",   # Coffee
    "WUSD",    # Wheat
    "CUSD",    # Corn
    "SUSD",    # Soybeans
    "VIXUSD",  # CBOE Volatility Index (VIX)
]


def _fetch_and_merge(symbols: list[str], start_date, end_date) -> pd.DataFrame | None:
    """Fetch commodity data per symbol and merge into a wide DataFrame."""
    merged: pd.DataFrame | None = None

    for symbol in symbols:
        df = get_commodity_prices(symbol=symbol, start_date=start_date, end_date=end_date)
        if df.empty:
            continue

        df = df[["date", "close", "volume"]].copy()
        df.rename(columns={"close": f"{symbol}_close", "volume": f"{symbol}_volume"}, inplace=True)

        if merged is None:
            merged = df
        else:
            merged = pd.merge(merged, df, on="date", how="outer")

    return merged


# ================================
# --> Tools
# ================================

@agent_tool(name="commodity_prices", category="market")
def commodity_prices(
    symbols: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": (
                "Commodity symbols to fetch. If omitted, fetches all 16.\n"
                "Valid: GCUSD (Gold), SIUSD (Silver), PLUSD (Platinum), PAUSD (Palladium), "
                "CLUSD (WTI Crude), BRUSD (Brent Crude), NGUSD (Natural Gas), HGUSD (Copper), "
                "ZSUSD (Sugar), CCUSD (Cocoa), CTUSD (Cotton), KCUSD (Coffee), "
                "WUSD (Wheat), CUSD (Corn), SUSD (Soybeans), "
                "VIXUSD (CBOE Volatility Index)"
            ),
            "items": {"type": "string", "enum": COMMODITY_SYMBOLS},
            "default": None,
        }),
    ] = None,
    days_back: Annotated[int, Param(min_val=1, max_val=60)] = 30,
) -> str:
    """Fetch recent daily commodity price data (close + volume).

Returns a wide-format table of daily close prices and volume for each
requested commodity symbol.

**Available Commodities (16 total):**
- Precious Metals: GCUSD (Gold), SIUSD (Silver), PLUSD (Platinum), PAUSD (Palladium)
- Energy: CLUSD (Crude Oil WTI), BRUSD (Brent Crude), NGUSD (Natural Gas)
- Industrial Metals: HGUSD (Copper)
- Agriculture - Softs: ZSUSD (Sugar), CCUSD (Cocoa), CTUSD (Cotton), KCUSD (Coffee)
- Agriculture - Grains: WUSD (Wheat), CUSD (Corn), SUSD (Soybeans)
- Volatility: VIXUSD (CBOE Volatility Index (VIX))

**Use Cases:**
- Gold price tracking: symbols=['GCUSD']
- Energy complex: symbols=['CLUSD', 'BRUSD', 'NGUSD']
- Precious metals basket: symbols=['GCUSD', 'SIUSD', 'PLUSD', 'PAUSD']
- Agricultural commodities: symbols=['WUSD', 'CUSD', 'SUSD']
- Volatility: symbols=['VIXUSD']
- All commodities: symbols=None (returns all 16)

    Args:
        symbols: Commodity symbols to fetch (default: all 16)
        days_back: Number of calendar days of history (default: 30, max: 60)

    Examples:
        commodity_prices(symbols=['GCUSD'])
        commodity_prices(symbols=['CLUSD', 'BRUSD', 'NGUSD'], days_back=60)
    """
    try:
        target_symbols = symbols if symbols is not None else COMMODITY_SYMBOLS

        # Reason: validate symbols against known list
        invalid = [s for s in target_symbols if s not in COMMODITY_SYMBOLS]
        if invalid:
            return error_response(f"Invalid commodity symbols: {invalid}. Valid: {COMMODITY_SYMBOLS}")

        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=days_back)

        merged = _fetch_and_merge(target_symbols, start_date, end_date)
        if merged is None or merged.empty:
            return success_response("No data available for the specified commodities.")

        merged["date"] = pd.to_datetime(merged["date"])
        merged = merged.sort_values("date")

        close_cols = [c for c in merged.columns if c.endswith("_close")]
        volume_cols = [c for c in merged.columns if c.endswith("_volume")]

        for c in close_cols:
            merged[c] = merged[c].round(3)
        for c in volume_cols:
            merged[c] = merged[c].fillna(0).astype(int)

        merged["date"] = merged["date"].astype(str)
        return success_response(merged.to_dict(orient="records"))

    except Exception as e:
        return error_response(f"Failed to fetch commodity prices: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(commodity_prices(symbols=["GCUSD", "CLUSD"], days_back=14))
