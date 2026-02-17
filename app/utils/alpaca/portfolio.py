"""
Alpaca Portfolio Management
Handles portfolio data retrieval: account info, positions, orders
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus
from typing import Optional, List, Dict
from app.utils.alpaca.client import AlpacaClient

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
        Get orders filtered by status

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

