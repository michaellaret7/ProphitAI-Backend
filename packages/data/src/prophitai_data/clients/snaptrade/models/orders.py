"""
SnapTrade Order Models
Flattens SnapTrade's AccountOrderRecord responses into clean Pydantic models.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ================================
# --> Helper funcs
# ================================

def _safe_float(value: Any) -> Optional[float]:
    """Convert a value to float, returning None if not possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_order(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten a single raw SnapTrade AccountOrderRecord into OrderRecord fields.

    Args:
        raw: Raw order dict from the SnapTrade API

    Returns:
        Flat dict matching OrderRecord fields
    """
    universal_symbol = raw.get("universal_symbol") or {}
    option_data = raw.get("option_symbol") or {}
    option_underlying = option_data.get("underlying_symbol") or {}

    # Reason: Options have ticker in option_symbol.underlying_symbol.symbol,
    # equities have it in universal_symbol.symbol
    is_option = bool(option_data)
    ticker = (
        option_underlying.get("symbol", "")
        if is_option
        else universal_symbol.get("symbol", "")
    )

    return {
        "brokerage_order_id": raw.get("brokerage_order_id", ""),
        "status": raw.get("status", ""),
        "ticker": ticker,
        "asset_type": "option" if is_option else "equity",
        "action": raw.get("action", ""),
        "order_type": raw.get("order_type"),
        "time_in_force": raw.get("time_in_force", ""),
        "total_quantity": _safe_float(raw.get("total_quantity")),
        "filled_quantity": _safe_float(raw.get("filled_quantity")),
        "open_quantity": _safe_float(raw.get("open_quantity")),
        "canceled_quantity": _safe_float(raw.get("canceled_quantity")),
        "execution_price": _safe_float(raw.get("execution_price")),
        "limit_price": _safe_float(raw.get("limit_price")),
        "stop_price": _safe_float(raw.get("stop_price")),
        "time_placed": raw.get("time_placed", ""),
        "time_updated": raw.get("time_updated"),
        "time_executed": raw.get("time_executed"),
        # Option-specific fields
        "option_ticker": option_data.get("ticker") if is_option else None,
        "strike_price": float(option_data["strike_price"]) if is_option and option_data.get("strike_price") else None,
        "expiration_date": option_data.get("expiration_date") if is_option else None,
        "option_type": option_data.get("option_type") if is_option else None,
    }


class OrderRecord(BaseModel):
    """A single order record flattened from SnapTrade's AccountOrderRecord."""

    model_config = {"frozen": True}

    brokerage_order_id: str
    status: str                                 # PENDING, EXECUTED, CANCELED, PARTIAL, etc.
    ticker: str
    asset_type: str                             # "equity" or "option"
    action: str                                 # BUY or SELL
    order_type: Optional[str] = None            # Market, Limit, Stop, StopLimit
    time_in_force: str = ""                     # Day, GTC, FOK, IOC
    total_quantity: Optional[float] = None
    filled_quantity: Optional[float] = None
    open_quantity: Optional[float] = None
    canceled_quantity: Optional[float] = None
    execution_price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_placed: Optional[str] = None
    time_updated: Optional[str] = None
    time_executed: Optional[str] = None
    # Option-specific (None for equities)
    option_ticker: Optional[str] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[str] = None
    option_type: Optional[str] = None           # PUT or CALL

    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "OrderRecord":
        """Create an OrderRecord from a single raw SnapTrade order dict."""
        return OrderRecord(**_parse_order(raw))

    @staticmethod
    def from_raw_list(raw_list: List[Dict[str, Any]]) -> List["OrderRecord"]:
        """Create a list of OrderRecords from raw SnapTrade order dicts."""
        return [OrderRecord(**_parse_order(r)) for r in raw_list]
