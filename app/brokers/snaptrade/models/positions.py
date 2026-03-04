"""
SnapTrade Position Model
Flattens the deeply nested SnapTrade position response into a clean Pydantic model.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field


class Position(BaseModel):
    """A single portfolio position flattened from SnapTrade's nested response."""

    model_config = {"frozen": True}

    ticker: str
    description: str
    exchange: str
    security_type: str
    currency: str
    units: float
    fractional_units: float
    price: float
    average_purchase_price: float
    open_pnl: float
    market_value: float
    cost_basis: float
    cash_equivalent: bool
    snaptrade_symbol_id: str
    figi_code: str

    @computed_field
    @property
    def pnl_pct(self) -> Optional[float]:
        """Unrealized PnL as a percentage of cost basis."""
        if self.cost_basis == 0:
            return None
        return round((self.open_pnl / self.cost_basis) * 100, 4)

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "Position":
        """Create a Position from a single raw SnapTrade position dict."""
        return _parse_position(raw)

    @staticmethod
    def from_raw_list(raw_list: List[Dict[str, Any]]) -> List["Position"]:
        """Create a list of Positions from the raw SnapTrade response."""
        return [_parse_position(p) for p in raw_list]


# ================================
# --> Helper funcs
# ================================

def _parse_position(raw: Dict[str, Any]) -> Position:
    """Parse a single raw SnapTrade position dict into a Position model."""
    symbol_data = raw.get("symbol", {})
    inner_symbol = symbol_data.get("symbol", {})
    exchange = inner_symbol.get("exchange", {})
    security_type = inner_symbol.get("type", {})
    currency = inner_symbol.get("currency", {})

    return Position(
        ticker=inner_symbol.get("symbol", ""),
        description=inner_symbol.get("description", ""),
        exchange=exchange.get("code", ""),
        security_type=security_type.get("description", ""),
        currency=currency.get("code", "USD"),
        units=raw.get("units", 0.0),
        fractional_units=raw.get("fractional_units", 0.0),
        price=raw.get("price", 0.0),
        average_purchase_price=raw.get("average_purchase_price", 0.0),
        open_pnl=raw.get("open_pnl", 0.0),
        market_value=round(raw.get("price", 0.0) * raw.get("units", 0.0), 2),
        cost_basis=round(
            raw.get("average_purchase_price", 0.0) * raw.get("units", 0.0), 2,
        ),
        cash_equivalent=raw.get("cash_equivalent", False),
        snaptrade_symbol_id=symbol_data.get("id", ""),
        figi_code=inner_symbol.get("figi_code", ""),
    )
