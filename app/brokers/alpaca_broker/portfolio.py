"""
Alpaca Broker Portfolio Management
Handles portfolio data retrieval: positions, orders, assets, and history.

Mirrors: app/brokers/alpaca/portfolio.py
Key difference: Every method takes account_id.
Assets are global (not per-account) — same as Trading API.
"""

from alpaca.broker.client import BrokerClient
from alpaca.trading.requests import GetAssetsRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from typing import Optional, List, Dict


class BrokerPortfolio:
    """Handles portfolio data retrieval for end user accounts."""

    def __init__(self, client: BrokerClient):
        self.client = client

    # ── Portfolio History ─────────────────────────────────────────

    def get_portfolio_history(
        self,
        account_id: str,
        period: Optional[str] = None,
        timeframe: Optional[str] = None,
        extended_hours: Optional[bool] = None,
    ) -> Dict:
        """
        Get historical portfolio equity and P&L over time.

        Args:
            account_id: User's Alpaca account ID
            period: '1D', '1W', '1M', '3M', '6M', '1A' (1 year), 'all'
            timeframe: '1Min', '5Min', '15Min', '1H', '1D'
            extended_hours: Include extended hours data

        Returns:
            Dict with parallel arrays: timestamp, equity, profit_loss, profit_loss_pct, base_value
        """
        try:
            history = self.client.get_portfolio_history_for_account(
                account_id=account_id,
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
        except Exception as e:
            raise Exception(f"Failed to get portfolio history for {account_id}: {str(e)}")

    # ── Assets (global, not per-account) ──────────────────────────

    def get_asset(self, symbol: str) -> Dict:
        """
        Get detailed info for a single asset.

        Args:
            symbol: Stock symbol (e.g., 'AAPL'), crypto pair (e.g., 'BTC/USD'),
                    or asset UUID

        Returns:
            Asset details dict with tradability, marginability, shortability, etc.
        """
        try:
            asset = self.client.get_asset(symbol)
            return self._format_asset(asset)
        except Exception as e:
            raise Exception(f"Failed to get asset {symbol}: {str(e)}")

    def get_all_assets(
        self,
        status: Optional[str] = None,
        asset_class: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get a list of all tradeable assets, optionally filtered.

        Args:
            status: 'active' or 'inactive'
            asset_class: 'us_equity', 'us_option', or 'crypto'

        Returns:
            List of asset detail dicts
        """
        status_enum = (
            {"active": AssetStatus.ACTIVE, "inactive": AssetStatus.INACTIVE}.get(
                status.lower()
            )
            if status
            else None
        )

        class_enum = (
            {
                "us_equity": AssetClass.US_EQUITY,
                "us_option": AssetClass.US_OPTION,
                "crypto": AssetClass.CRYPTO,
            }.get(asset_class.lower())
            if asset_class
            else None
        )

        try:
            assets = self.client.get_all_assets(
                filter=GetAssetsRequest(status=status_enum, asset_class=class_enum)
            )
            return [self._format_asset(a) for a in assets]
        except Exception as e:
            raise Exception(f"Failed to get assets: {str(e)}")

    @staticmethod
    def _format_asset(asset) -> Dict:
        """Format an Asset model into a standardized dict."""
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
