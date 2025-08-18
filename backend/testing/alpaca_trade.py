"""
Simple Alpaca Trading Class
A straightforward wrapper for buying and selling assets on Alpaca Markets
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, 
    LimitOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from typing import Optional, Union, List, Dict


class AlpacaTrader:
    """Simple class for trading on Alpaca Markets"""
    
    def __init__(self, paper: bool = True):
        """
        Initialize the Alpaca trader
        
        Args:
            api_key: Your Alpaca API key
            secret_key: Your Alpaca secret key
            paper: Use paper trading (True) or live trading (False)
        """
        self.api_key = "PKBJQF04EN267R5OFH09"
        self.secret_key = "CW1NAvvBvlErPte4AFR4B3jNmUNzKP0lEe9cI6Fl"
        self.client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.paper = paper

    def get_account(self) -> Dict:
        """Get account information"""
        account = self.client.get_account()
        return {
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'equity': float(account.equity),
            'account_number': account.account_number,
            'status': account.status,
            'pattern_day_trader': account.pattern_day_trader
        }
    
    def buy(self, 
            symbol: str, 
            qty: Optional[float] = None,
            notional: Optional[float] = None,
            limit_price: Optional[float] = None,
            time_in_force: str = 'day') -> Dict:
        """
        Buy an asset
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL') or crypto pair (e.g., 'BTC/USD')
            qty: Number of shares to buy (use either qty or notional, not both)
            notional: Dollar amount to spend (use either qty or notional, not both)
            limit_price: If set, creates a limit order at this price. If None, creates market order
            time_in_force: 'day', 'gtc' (good till canceled), 'ioc' (immediate or cancel), 'fok' (fill or kill)
            
        Returns:
            Order details
        """
        # Map string time_in_force to enum
        tif_map = {
            'day': TimeInForce.DAY,
            'gtc': TimeInForce.GTC,
            'ioc': TimeInForce.IOC,
            'fok': TimeInForce.FOK
        }
        tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)
        
        try:
            if limit_price:
                # Limit order
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=OrderSide.BUY,
                    time_in_force=tif,
                    limit_price=limit_price
                )
            else:
                # Market order
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=OrderSide.BUY,
                    time_in_force=tif
                )
            
            order = self.client.submit_order(order_data=order_data)
            
            return {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None,
                'notional': float(order.notional) if order.notional else None,
                'side': order.side,
                'type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            raise Exception(f"Failed to buy {symbol}: {str(e)}")
    
    def sell(self, 
             symbol: str, 
             qty: Optional[float] = None,
             notional: Optional[float] = None,
             limit_price: Optional[float] = None,
             time_in_force: str = 'day') -> Dict:
        """
        Sell an asset
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL') or crypto pair (e.g., 'BTC/USD')
            qty: Number of shares to sell (use either qty or notional, not both)
            notional: Dollar amount to sell (use either qty or notional, not both)
            limit_price: If set, creates a limit order at this price. If None, creates market order
            time_in_force: 'day', 'gtc' (good till canceled), 'ioc' (immediate or cancel), 'fok' (fill or kill)
            
        Returns:
            Order details
        """
        # Map string time_in_force to enum
        tif_map = {
            'day': TimeInForce.DAY,
            'gtc': TimeInForce.GTC,
            'ioc': TimeInForce.IOC,
            'fok': TimeInForce.FOK
        }
        tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)
        
        try:
            if limit_price:
                # Limit order
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=OrderSide.SELL,
                    time_in_force=tif,
                    limit_price=limit_price
                )
            else:
                # Market order
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=OrderSide.SELL,
                    time_in_force=tif
                )
            
            order = self.client.submit_order(order_data=order_data)
            
            return {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None,
                'notional': float(order.notional) if order.notional else None,
                'side': order.side,
                'type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            raise Exception(f"Failed to sell {symbol}: {str(e)}")
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
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
        """Get position for a specific symbol"""
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
        except:
            return None
    
    def close_position(self, symbol: str) -> Dict:
        """Close a position for a specific symbol"""
        try:
            order = self.client.close_position(symbol)
            return {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None,
                'status': order.status
            }
        except Exception as e:
            raise Exception(f"Failed to close position for {symbol}: {str(e)}")
    
    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        """Close all positions"""
        try:
            orders = self.client.close_all_positions(cancel_orders=cancel_orders)
            return [
                {
                    'id': str(order.id),
                    'symbol': order.symbol,
                    'status': order.status
                }
                for order in orders
            ]
        except Exception as e:
            raise Exception(f"Failed to close all positions: {str(e)}")
    
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """
        Get orders
        
        Args:
            status: 'open', 'closed', 'all'
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
    
    def cancel_order(self, order_id: str) -> None:
        """Cancel a specific order"""
        try:
            self.client.cancel_order_by_id(order_id)
        except Exception as e:
            raise Exception(f"Failed to cancel order {order_id}: {str(e)}")
    
    def cancel_all_orders(self) -> None:
        """Cancel all open orders"""
        try:
            self.client.cancel_orders()
        except Exception as e:
            raise Exception(f"Failed to cancel all orders: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Initialize trader (paper trading by default)
    trader = AlpacaTrader(paper=True)  # Use paper trading for testing
    
    # Check account info
    account = trader.get_account()
    print(f"Buying Power: ${account['buying_power']:,.2f}")
    print(f"Account Equity: ${account['equity']:,.2f}")
    
    # Buy $1000 worth of Apple stock (market order)
    order = trader.buy(symbol='AAPL', notional=1000)
    print(f"Bought AAPL - Order ID: {order['id']}")
    
    # Buy 10 shares of Tesla with a limit price
    # order = trader.buy(symbol='TSLA', qty=10, limit_price=200.00)
    # print(f"Limit order placed for TSLA")
    
    # Sell 5 shares of Microsoft
    # order = trader.sell(symbol='MSFT', qty=5)
    # print(f"Sold MSFT - Order ID: {order['id']}")
    
    # Get all positions
    # positions = trader.get_positions()
    # for pos in positions:
    #     print(f"{pos['symbol']}: {pos['qty']} shares, P/L: ${pos['unrealized_pl']:,.2f}")
    
    # Close a specific position
    # trader.close_position('AAPL')
    
    # Get open orders
    # orders = trader.get_orders(status='open')
    # for order in orders:
    #     print(f"Open order: {order['symbol']} - {order['side']} {order['qty']} shares")






