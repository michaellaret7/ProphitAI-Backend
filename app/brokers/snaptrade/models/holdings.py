"""
SnapTrade Portfolio Models
Flattens the deeply nested SnapTrade responses into clean Pydantic models.
Parses equity positions, orders, option positions, and total portfolio value.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field


class Position(BaseModel):
    """A single equity position flattened from SnapTrade's nested response."""

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
    position_type: str = "equity"

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


class Order(BaseModel):
    """A single order flattened from SnapTrade's nested holdings response."""

    model_config = {"frozen": True}

    brokerage_order_id: str
    status: str
    ticker: str
    description: str
    action: str
    total_quantity: float
    filled_quantity: float
    execution_price: Optional[float] = None
    order_type: str
    time_in_force: str
    time_placed: str
    time_executed: Optional[str] = None

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "Order":
        """Create an Order from a single raw SnapTrade order dict."""
        return _parse_order(raw)

    @staticmethod
    def from_raw_list(raw_list: List[Dict[str, Any]]) -> List["Order"]:
        """Create a list of Orders from the raw SnapTrade response."""
        return [_parse_order(o) for o in raw_list]


class OptionPosition(BaseModel):
    """A single option position flattened from SnapTrade's nested holdings response."""

    model_config = {"frozen": True}

    ticker: str
    underlying_ticker: str
    strike_price: float
    expiration_date: str
    option_type: str
    price: float
    units: float
    average_purchase_price: float
    position_type: str = "option"

    @computed_field
    @property
    def market_value(self) -> float:
        """Market value: price * units * 100 (each contract = 100 shares)."""
        return round(self.price * self.units * 100, 2)

    @computed_field
    @property
    def cost_basis(self) -> float:
        """Cost basis: average_purchase_price * units * 100."""
        return round(self.average_purchase_price * self.units * 100, 2)

    @computed_field
    @property
    def open_pnl(self) -> float:
        """Unrealized P&L."""
        return round(self.market_value - self.cost_basis, 2)

    @computed_field
    @property
    def pnl_pct(self) -> Optional[float]:
        """Unrealized PnL as a percentage of cost basis."""
        if self.cost_basis == 0:
            return None
        return round((self.open_pnl / self.cost_basis) * 100, 4)

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "OptionPosition":
        """Create an OptionPosition from a single raw SnapTrade option position dict."""
        return _parse_option_position(raw)

    @staticmethod
    def from_raw_list(raw_list: List[Dict[str, Any]]) -> List["OptionPosition"]:
        """Create a list of OptionPositions from the raw SnapTrade response."""
        return [_parse_option_position(op) for op in raw_list]


class STPortfolio(BaseModel):
    """Parsed portfolio snapshot: equity + option positions from SnapTrade."""

    model_config = {"frozen": True}

    equity_positions: List[Position]
    option_positions: List[OptionPosition]

    @staticmethod
    def from_raw(
        equity_raw: List[Dict[str, Any]],
        options_raw: List[Dict[str, Any]],
    ) -> "STPortfolio":
        """Build an STPortfolio from raw SnapTrade API response lists."""
        return STPortfolio(
            equity_positions=Position.from_raw_list(equity_raw),
            option_positions=OptionPosition.from_raw_list(options_raw),
        )


# ================================
# --> Helper funcs
# ================================

def _parse_position(raw: Dict[str, Any]) -> Position:
    """Parse a single raw SnapTrade position dict into a Position model."""
    symbol_data = raw.get("symbol") or {}
    inner_symbol = symbol_data.get("symbol") or {}
    exchange = inner_symbol.get("exchange") or {}
    security_type = inner_symbol.get("type") or {}
    currency = inner_symbol.get("currency") or {}

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


def _parse_order(raw: Dict[str, Any]) -> Order:
    """Parse a single raw SnapTrade order dict into an Order model."""
    universal_symbol = raw.get("universal_symbol") or {}

    return Order(
        brokerage_order_id=raw.get("brokerage_order_id") or "",
        status=raw.get("status") or "",
        ticker=universal_symbol.get("symbol") or "",
        description=universal_symbol.get("description") or "",
        action=raw.get("action") or "",
        total_quantity=raw.get("total_quantity") or 0.0,
        filled_quantity=raw.get("filled_quantity") or 0.0,
        execution_price=raw.get("execution_price"),
        order_type=raw.get("order_type") or "",
        time_in_force=raw.get("time_in_force") or "",
        time_placed=raw.get("time_placed") or "",
        time_executed=raw.get("time_executed"),
    )


def _parse_option_position(raw: Dict[str, Any]) -> OptionPosition:
    """Parse a single raw SnapTrade option position dict into an OptionPosition model."""
    symbol_data = raw.get("symbol") or {}
    option_symbol = symbol_data.get("option_symbol") or {}
    underlying = option_symbol.get("underlying_symbol") or {}

    return OptionPosition(
        ticker=symbol_data.get("description", ""),
        underlying_ticker=underlying.get("symbol", ""),
        strike_price=option_symbol.get("strike_price", 0.0),
        expiration_date=option_symbol.get("expiration_date", ""),
        option_type=option_symbol.get("option_type", ""),
        price=raw.get("price", 0.0),
        units=raw.get("units", 0.0),
        average_purchase_price=raw.get("average_purchase_price", 0.0),
    )
