"""
Alpaca Portfolio Management
Handles portfolio data retrieval: account info, positions, orders, assets, and history
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest, GetAssetsRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import QueryOrderStatus, AssetClass, AssetStatus
from typing import Optional, List, Dict

class AlpacaPortfolio:
    """Handles portfolio data retrieval and account information"""

    def __init__(self, client: TradingClient):
        """
        Initialize portfolio operations

        Args:
            client: Initialized TradingClient instance
        """
        self.client = client

    def get_account(self) -> Dict:
        """
        Get account information

        Returns:
            Account details dict with buying_power, cash, equity, etc.
        """
        account = self.client.get_account()
        return {
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'equity': float(account.equity),
            'account_number': account.account_number,
            'status': account.status,
            'pattern_day_trader': account.pattern_day_trader
        }

    def get_positions(self) -> List[Dict]:
        """
        Get all current positions

        Returns:
            List of position dicts
        """
        positions = self.client.get_all_positions()
        return [
            {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                'unrealized_plpc': float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                'side': pos.side
            }
            for pos in positions
        ]

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol

        Args:
            symbol: Symbol to get position for

        Returns:
            Position dict or None if no position exists
        """
        try:
            pos = self.client.get_open_position(symbol)
            return {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                'unrealized_plpc': float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                'side': pos.side
            }
        except Exception:
            return None

    def get_orders(self, status: str = 'open') -> List[Dict]:
        """
        Get orders filtered by status.

        Args:
            status: 'open', 'closed', or 'all'

        Returns:
            List of order dicts
        """
        status_map = {
            'open': QueryOrderStatus.OPEN,
            'closed': QueryOrderStatus.CLOSED,
            'all': QueryOrderStatus.ALL
        }

        request_params = GetOrdersRequest(
            status=status_map.get(status.lower(), QueryOrderStatus.OPEN)
        )

        orders = self.client.get_orders(filter=request_params)

        return [
            {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None,
                'side': order.side,
                'type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at
            }
            for order in orders
        ]

    def get_portfolio_history(
        self,
        period: Optional[str] = None,
        timeframe: Optional[str] = None,
        extended_hours: Optional[bool] = None,
    ) -> Dict:
        """
        Get historical portfolio equity and P&L over time.

        Args:
            period: Duration — '1D', '1W', '1M', '3M', '6M', '1A' (1 year), 'all'
            timeframe: Resolution — '1Min', '5Min', '15Min', '1H', '1D'
            extended_hours: Include extended hours data

        Returns:
            Dict with parallel arrays: timestamp, equity, profit_loss, profit_loss_pct, base_value
        """
        history = self.client.get_portfolio_history(
            history_filter=GetPortfolioHistoryRequest(
                period=period,
                timeframe=timeframe,
                extended_hours=extended_hours,
            )
        )
        return {
            'timestamp': history.timestamp,
            'equity': history.equity,
            'profit_loss': history.profit_loss,
            'profit_loss_pct': history.profit_loss_pct,
            'base_value': history.base_value,
            'timeframe': history.timeframe,
        }

    def get_asset(self, symbol: str) -> Dict:
        """
        Get detailed info for a single asset.

        Args:
            symbol: Stock symbol (e.g., 'AAPL'), crypto pair (e.g., 'BTC/USD'), or asset UUID

        Returns:
            Asset details dict with tradability, marginability, shortability, etc.
        """
        asset = self.client.get_asset(symbol)
        return self._format_asset(asset)

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
        status_enum = {'active': AssetStatus.ACTIVE, 'inactive': AssetStatus.INACTIVE}.get(
            status.lower()
        ) if status else None

        class_enum = {
            'us_equity': AssetClass.US_EQUITY,
            'us_option': AssetClass.US_OPTION,
            'crypto': AssetClass.CRYPTO,
        }.get(asset_class.lower()) if asset_class else None

        assets = self.client.get_all_assets(
            filter=GetAssetsRequest(status=status_enum, asset_class=class_enum)
        )
        return [self._format_asset(a) for a in assets]

    @staticmethod
    def _format_asset(asset) -> Dict:
        """Format an Asset model into a standardized dict."""
        return {
            'id': str(asset.id),
            'symbol': asset.symbol,
            'name': asset.name,
            'asset_class': asset.asset_class,
            'exchange': asset.exchange,
            'status': asset.status,
            'tradable': asset.tradable,
            'fractionable': asset.fractionable,
            'marginable': asset.marginable,
            'shortable': asset.shortable,
            'easy_to_borrow': asset.easy_to_borrow,
            'min_order_size': asset.min_order_size,
            'min_trade_increment': asset.min_trade_increment,
            'price_increment': asset.price_increment,
            'maintenance_margin_requirement': asset.maintenance_margin_requirement,
        }

