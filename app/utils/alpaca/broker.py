"""Alpaca Unified Interface - One-stop shop for all Alpaca trading operations."""
from typing import Optional, List, Dict, Tuple
from app.utils.alpaca.client import AlpacaClient
from app.utils.alpaca.trading import AlpacaTrading
from app.utils.alpaca.portfolio import AlpacaPortfolio
from app.utils.alpaca.options import OptionsService

class Alpaca:
    """
    Unified interface for all Alpaca operations.

    Usage:
        alpaca = Alpaca()  # Uses env vars for credentials
        alpaca = Alpaca(api_key='...', secret_key='...', paper=True)

        # Convenience methods
        alpaca.buy('AAPL', qty=10)
        alpaca.sell('AAPL', qty=5)
        alpaca.get_account()

        # Direct sub-component access
        alpaca.trading.close_all_positions()
        alpaca.options.get_options_chain('SPY')
    """

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        secret_key: Optional[str] = None,
        paper: bool = True, 
        options_feed: str = "indicative"
    ):
        self.client = AlpacaClient(api_key=api_key, secret_key=secret_key, paper=paper)
        self.trading = AlpacaTrading(self.client.get_client())
        self.portfolio = AlpacaPortfolio(self.client.get_client())
        self.options = OptionsService(self.client, feed=options_feed)

    # Account & Portfolio
    def get_account(self) -> Dict:
        return self.portfolio.get_account()

    def get_buying_power(self) -> float:
        return self.portfolio.get_account()['buying_power']

    def get_cash(self) -> float:
        return self.portfolio.get_account()['cash']

    def get_equity(self) -> float:
        return self.portfolio.get_account()['equity']

    def get_positions(self) -> List[Dict]:
        return self.portfolio.get_positions()

    def get_position(self, symbol: str) -> Optional[Dict]:
        return self.portfolio.get_position(symbol)

    def get_orders(self, status: str = 'open') -> List[Dict]:
        return self.portfolio.get_orders(status)

    # Trading
    def buy(self, symbol: str, qty: Optional[float] = None, notional: Optional[float] = None, limit_price: Optional[float] = None, stop_price: Optional[float] = None, take_profit: Optional[float] = None, stop_loss: Optional[float] = None, time_in_force: str = 'day') -> Dict:
        return self.trading.buy(symbol=symbol, qty=qty, notional=notional, limit_price=limit_price, stop_price=stop_price, take_profit=take_profit, stop_loss=stop_loss, time_in_force=time_in_force)

    def sell(self, symbol: str, qty: Optional[float] = None, notional: Optional[float] = None, limit_price: Optional[float] = None, stop_price: Optional[float] = None, take_profit: Optional[float] = None, stop_loss: Optional[float] = None, time_in_force: str = 'day') -> Dict:
        return self.trading.sell(symbol=symbol, qty=qty, notional=notional, limit_price=limit_price, stop_price=stop_price, take_profit=take_profit, stop_loss=stop_loss, time_in_force=time_in_force)

    def close_position(self, symbol: str) -> Dict:
        return self.trading.close_position(symbol)

    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        return self.trading.close_all_positions(cancel_orders)

    def cancel_order(self, order_id: str) -> None:
        self.trading.cancel_order(order_id)

    def cancel_all_orders(self) -> None:
        self.trading.cancel_all_orders()

    # Options
    def get_options_chain(self, underlying: str, expiration: Optional[str] = None, limit: Optional[int] = None, return_df: Optional[bool] = None):
        return self.options.get_options_chain(underlying=underlying, expiration=expiration, limit=limit, return_df=return_df)

    def get_option_expirations(self, underlying: str, start: Optional[str] = None, end: Optional[str] = None) -> List[str]:
        return self.options.get_available_dates(underlying=underlying, start=start, end=end)

    def get_option_contracts(self, underlying: str, expiration: Optional[str] = None, contract_type: Optional[str] = None, strike_range: Optional[Tuple[float, float]] = None, limit: Optional[int] = None) -> List[str]:
        return self.options.get_available_contracts(underlying=underlying, expiration=expiration, contract_type=contract_type, strike_range=strike_range, limit=limit)

    def buy_option(self, symbol: str, qty: int = 1, limit_price: Optional[float] = None, time_in_force: str = 'day') -> Dict:
        return self.trading.buy(symbol=symbol, qty=qty, limit_price=limit_price, time_in_force=time_in_force)

    def sell_option(self, symbol: str, qty: int = 1, limit_price: Optional[float] = None, time_in_force: str = 'day') -> Dict:
        return self.trading.sell(symbol=symbol, qty=qty, limit_price=limit_price, time_in_force=time_in_force)

    # Utilities
    def is_paper(self) -> bool:
        return self.client.is_paper_trading()

