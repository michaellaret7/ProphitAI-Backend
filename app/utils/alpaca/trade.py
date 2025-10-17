"""
Alpaca Trading Unified Interface
Combines client connection, trading operations, and portfolio management
"""

from typing import Optional, List, Dict
from .client import AlpacaClient
from .trading import AlpacaTrading
from .portfolio import AlpacaPortfolio


class AlpacaTrader:
    """
    Unified interface for Alpaca trading operations
    Delegates to specialized modules for connection, trading, and portfolio management
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True
    ):
        """
        Initialize the Alpaca trader

        Args:
            api_key: Alpaca API key (defaults to env variable ALPACA_API_KEY)
            secret_key: Alpaca secret key (defaults to env variable ALPACA_SECRET_KEY)
            paper: Use paper trading (True) or live trading (False)
        """
        # Initialize client connection
        self._client = AlpacaClient(api_key, secret_key, paper)

        # Initialize specialized modules
        self.trading = AlpacaTrading(self._client.get_client())
        self.portfolio = AlpacaPortfolio(self._client.get_client())

    # Delegation methods for convenient access
    # Trading operations
    def buy(self, symbol: str, qty: Optional[float] = None,
            notional: Optional[float] = None, limit_price: Optional[float] = None,
            time_in_force: str = 'day') -> Dict:
        """Buy an asset - delegates to AlpacaTrading"""
        return self.trading.buy(symbol, qty, notional, limit_price, time_in_force)

    def sell(self, symbol: str, qty: Optional[float] = None,
             notional: Optional[float] = None, limit_price: Optional[float] = None,
             time_in_force: str = 'day') -> Dict:
        """Sell an asset - delegates to AlpacaTrading"""
        return self.trading.sell(symbol, qty, notional, limit_price, time_in_force)

    def close_position(self, symbol: str) -> Dict:
        """Close a position - delegates to AlpacaTrading"""
        return self.trading.close_position(symbol)

    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        """Close all positions - delegates to AlpacaTrading"""
        return self.trading.close_all_positions(cancel_orders)

    def cancel_order(self, order_id: str) -> None:
        """Cancel an order - delegates to AlpacaTrading"""
        return self.trading.cancel_order(order_id)

    def cancel_all_orders(self) -> None:
        """Cancel all orders - delegates to AlpacaTrading"""
        return self.trading.cancel_all_orders()

    # Portfolio operations
    def get_account(self) -> Dict:
        """Get account information - delegates to AlpacaPortfolio"""
        return self.portfolio.get_account()

    def get_positions(self) -> List[Dict]:
        """Get all positions - delegates to AlpacaPortfolio"""
        return self.portfolio.get_positions()

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for specific symbol - delegates to AlpacaPortfolio"""
        return self.portfolio.get_position(symbol)

    def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders - delegates to AlpacaPortfolio"""
        return self.portfolio.get_orders(status)

    @property
    def is_paper_trading(self) -> bool:
        """Check if using paper trading"""
        return self._client.is_paper_trading()


# Example usage
if __name__ == "__main__":
    # Initialize trader (paper trading by default)
    # API keys will be read from ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables
    trader = AlpacaTrader(paper=True)

    # Check account info
    account = trader.get_account()
    print(f"Buying Power: ${account['buying_power']:,.2f}")
    print(f"Account Equity: ${account['equity']:,.2f}")

    # Buy $1000 worth of Apple stock (market order)
    order = trader.buy(symbol='AAPL', notional=1000)
    print(f"Bought AAPL - Order ID: {order['id']}")

    # Get all positions
    positions = trader.get_positions()
    for pos in positions:
        print(f"{pos['symbol']}: {pos['qty']} shares, P/L: ${pos['unrealized_pl']:,.2f}")

    # Alternative: Access modules directly for more control
    # trading_module = trader.trading
    # portfolio_module = trader.portfolio
    # order = trading_module.buy('TSLA', qty=10, limit_price=200.00)
    # positions = portfolio_module.get_positions()






