"""Alpaca portfolio + account data retrieval.

Reads account info, positions, orders, assets, and historical equity from
the Alpaca trading client. Also assembles the ``BrokerStartupSnapshot``
that the live engine consumes at startup to hydrate its mirror state.
"""

from __future__ import annotations

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass, AssetStatus, QueryOrderStatus
from alpaca.trading.requests import (
    GetAssetsRequest,
    GetOrdersRequest,
    GetPortfolioHistoryRequest,
)

from prophitai_algo_trading.brokers.snapshots import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStartupSnapshot,
)
from prophitai_algo_trading.core.enums import Direction
from prophitai_shared import get_current_utc_time


#     ================================
# --> Helper funcs
#     ================================

_STATUS_MAP = {
    "open": QueryOrderStatus.OPEN,
    "closed": QueryOrderStatus.CLOSED,
    "all": QueryOrderStatus.ALL,
}

_ASSET_STATUS_MAP = {
    "active": AssetStatus.ACTIVE,
    "inactive": AssetStatus.INACTIVE,
}

_ASSET_CLASS_MAP = {
    "us_equity": AssetClass.US_EQUITY,
    "us_option": AssetClass.US_OPTION,
    "crypto": AssetClass.CRYPTO,
}


def _format_position(pos) -> dict:
    return {
        "symbol": pos.symbol,
        "qty": float(pos.qty),
        "avg_entry_price": float(pos.avg_entry_price),
        "entry_date": getattr(pos, "entry_date", None),
        "market_value": float(pos.market_value),
        "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0,
        "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
        "side": pos.side,
    }


def _format_order(order) -> dict:
    return {
        "id": str(order.id),
        "symbol": order.symbol,
        "qty": float(order.qty) if order.qty else None,
        "side": order.side,
        "type": order.order_type,
        "status": order.status,
        "limit_price": float(order.limit_price) if order.limit_price else None,
        "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
        "filled_avg_price": (
            float(order.filled_avg_price) if order.filled_avg_price else None
        ),
        "submitted_at": order.submitted_at,
        "filled_at": order.filled_at,
    }


def _format_asset(asset) -> dict:
    return {
        "id": str(asset.id),
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_class": asset.asset_class,
        "exchange": asset.exchange,
        "status": asset.status,
        "tradable": asset.tradable,
        "fractionable": asset.fractionable,
        "marginable": asset.marginable,
        "shortable": asset.shortable,
        "easy_to_borrow": asset.easy_to_borrow,
        "min_order_size": asset.min_order_size,
        "min_trade_increment": asset.min_trade_increment,
        "price_increment": asset.price_increment,
        "maintenance_margin_requirement": asset.maintenance_margin_requirement,
    }


def _normalize_position(pos_dict: dict) -> BrokerPositionSnapshot:
    side = str(pos_dict["side"]).lower()
    direction = Direction.SHORT if side == "short" else Direction.LONG

    return BrokerPositionSnapshot(
        symbol=pos_dict["symbol"],
        shares=abs(float(pos_dict["qty"])),
        direction=direction,
        entry_price=float(pos_dict["avg_entry_price"]),
        entry_date=pos_dict.get("entry_date"),
    )


def _normalize_order(order_dict: dict) -> BrokerOrderSnapshot:
    return BrokerOrderSnapshot(
        order_id=str(order_dict["id"]),
        symbol=order_dict["symbol"],
        side=str(order_dict["side"]),
        qty=order_dict.get("qty"),
        status=str(order_dict["status"]),
        order_type=str(order_dict["type"]),
    )


#     ================================
# --> Public service
#     ================================

class AlpacaPortfolio:
    """Account, position, order, and asset reads against the Alpaca API."""

    def __init__(self, client: TradingClient):
        self.client = client

    def get_account(self) -> dict:
        """Buying power, cash, equity, account status."""
        account = self.client.get_account()

        return {
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "equity": float(account.equity),
            "account_number": account.account_number,
            "status": account.status,
            "pattern_day_trader": account.pattern_day_trader,
        }

    def get_positions(self) -> list[dict]:
        """Every open position on the account."""
        positions = self.client.get_all_positions()

        return [_format_position(pos) for pos in positions]

    def get_position(self, symbol: str) -> dict | None:
        """One open position by symbol, or ``None`` if flat."""
        try:
            pos = self.client.get_open_position(symbol)
        except Exception:
            # Reason: Alpaca raises a generic exception when the symbol has
            # no open position; treat as "flat" rather than propagating.
            return None

        return _format_position(pos)

    def get_orders(self, status: str = "open") -> list[dict]:
        """Orders filtered by ``status`` (``open`` / ``closed`` / ``all``)."""
        request = GetOrdersRequest(
            status=_STATUS_MAP.get(status.lower(), QueryOrderStatus.OPEN),
        )

        orders = self.client.get_orders(filter=request)

        return [_format_order(order) for order in orders]

    def get_portfolio_history(
        self,
        period: str | None = None,
        timeframe: str | None = None,
        extended_hours: bool | None = None,
    ) -> dict:
        """Historical equity / P&L curves over ``period`` at ``timeframe``."""
        history = self.client.get_portfolio_history(
            history_filter=GetPortfolioHistoryRequest(
                period=period,
                timeframe=timeframe,
                extended_hours=extended_hours,
            ),
        )

        return {
            "timestamp": history.timestamp,
            "equity": history.equity,
            "profit_loss": history.profit_loss,
            "profit_loss_pct": history.profit_loss_pct,
            "base_value": history.base_value,
            "timeframe": history.timeframe,
        }

    def get_asset(self, symbol: str) -> dict:
        """Tradability / marginability / shortability for one asset."""
        asset = self.client.get_asset(symbol)

        return _format_asset(asset)

    def get_all_assets(
        self,
        status: str | None = None,
        asset_class: str | None = None,
    ) -> list[dict]:
        """Every tradeable asset, optionally filtered by status and class."""
        status_enum = _ASSET_STATUS_MAP.get(status.lower()) if status else None
        class_enum = (
            _ASSET_CLASS_MAP.get(asset_class.lower()) if asset_class else None
        )

        assets = self.client.get_all_assets(
            filter=GetAssetsRequest(status=status_enum, asset_class=class_enum),
        )

        return [_format_asset(asset) for asset in assets]

    def get_startup_snapshot(self) -> BrokerStartupSnapshot:
        """Assemble the snapshot the live engine uses to hydrate at startup."""
        account = self.get_account()
        positions = self.get_positions()
        open_orders = self.get_orders(status="open")

        return BrokerStartupSnapshot(
            cash=account["cash"],
            equity=account["equity"],
            positions=[_normalize_position(p) for p in positions],
            open_orders=[_normalize_order(o) for o in open_orders],
            captured_at=get_current_utc_time(),
        )
