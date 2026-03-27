"""
SnapTrade Activity Models
Flattens SnapTrade's nested activity responses into clean Pydantic models.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ================================
# --> Helper funcs
# ================================

def _parse_activity(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten a single raw SnapTrade activity dict into ActivityRecord fields.

    Args:
        raw: Raw activity dict from the SnapTrade API

    Returns:
        Flat dict matching ActivityRecord fields
    """
    symbol_data = raw.get("symbol") or {}
    option_data = raw.get("option_symbol") or {}
    option_underlying = option_data.get("underlying_symbol") or {}

    # Reason: Options have ticker in option_symbol.underlying_symbol.symbol,
    # equities have it in symbol.symbol
    is_option = bool(option_data)
    ticker = (
        option_underlying.get("symbol", "")
        if is_option
        else symbol_data.get("symbol", "")
    )

    return {
        "id": raw.get("id", ""),
        "ticker": ticker,
        "description": raw.get("description", ""),
        "type": raw.get("type", ""),
        "asset_type": "option" if is_option else "equity",
        "amount": float(raw.get("amount", 0)),
        "price": float(raw.get("price", 0)),
        "units": float(raw.get("units", 0)),
        "trade_date": raw.get("trade_date", ""),
        "settlement_date": raw.get("settlement_date", ""),
        # Option-specific fields
        "option_ticker": option_data.get("ticker") if is_option else None,
        "strike_price": float(option_data["strike_price"]) if is_option and option_data.get("strike_price") else None,
        "expiration_date": option_data.get("expiration_date") if is_option else None,
        "option_type": option_data.get("option_type") if is_option else None,
    }


class ActivityRecord(BaseModel):
    """A single activity record flattened from SnapTrade's nested response."""

    model_config = {"frozen": True}

    id: str
    ticker: str
    description: str
    type: str                           # BUY or SELL
    asset_type: str                     # "equity" or "option"
    amount: float                       # dollar amount (negative = outflow)
    price: float
    units: float                        # negative = sold/shorted
    trade_date: str
    settlement_date: str
    # Option-specific (None for equities)
    option_ticker: Optional[str] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[str] = None
    option_type: Optional[str] = None   # PUT or CALL

    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "ActivityRecord":
        """Create an ActivityRecord from a single raw SnapTrade activity dict."""
        return ActivityRecord(**_parse_activity(raw))

    @staticmethod
    def from_raw_list(raw_list: List[Dict[str, Any]]) -> List["ActivityRecord"]:
        """Create a list of ActivityRecords from raw SnapTrade activity dicts."""
        return [ActivityRecord(**_parse_activity(r)) for r in raw_list]
