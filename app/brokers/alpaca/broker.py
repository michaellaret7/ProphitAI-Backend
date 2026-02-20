"""Alpaca Unified Interface - One-stop shop for all Alpaca trading operations."""
from typing import Optional, List, Dict, Tuple
from app.brokers.alpaca.client import AlpacaClient
from app.brokers.alpaca.trading import AlpacaTrading
from app.brokers.alpaca.portfolio import AlpacaPortfolio
from app.brokers.alpaca.options import OptionsService


class Alpaca:
    """
    Unified interface for all Alpaca operations.

    Usage:
        alpaca = Alpaca()  # Uses env vars for credentials
        alpaca = Alpaca(api_key='...', secret_key='...', paper=True)

        # Simple orders
        alpaca.buy('AAPL', qty=10)
        alpaca.sell('AAPL', qty=5)

        # Trailing stop
        alpaca.sell('AAPL', qty=10, trail_percent=2.0)

        # Bracket order (entry + take profit + stop loss)
        alpaca.buy('AAPL', qty=10, take_profit=160, stop_loss=140, order_class='bracket')

        # Portfolio & assets
        alpaca.get_portfolio_history(period='1M', timeframe='1D')
        alpaca.get_asset('AAPL')

        # Direct sub-component access
        alpaca.trading.close_all_positions()
        alpaca.options.get_options_chain('SPY')
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
        options_feed: str = "indicative",
    ):
        self.client = AlpacaClient(api_key=api_key, secret_key=secret_key, paper=paper)
        self.trading = AlpacaTrading(self.client.get_client())
        self.portfolio = AlpacaPortfolio(self.client.get_client())
        self.options = OptionsService(self.client, feed=options_feed)

    # ── Account & Portfolio ──────────────────────────────────────────

    def get_account(self) -> Dict:
        """Get account information (buying_power, cash, equity, etc.)."""
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

    def get_portfolio_history(
        self,
        period: Optional[str] = None,
        timeframe: Optional[str] = None,
        extended_hours: Optional[bool] = None,
    ) -> Dict:
        """
        Get historical portfolio equity and P&L over time.

        Args:
            period: '1D', '1W', '1M', '3M', '6M', '1A', 'all'
            timeframe: '1Min', '5Min', '15Min', '1H', '1D'
            extended_hours: Include extended hours data
        """
        return self.portfolio.get_portfolio_history(
            period=period, timeframe=timeframe, extended_hours=extended_hours,
        )

    # ── Assets ───────────────────────────────────────────────────────

    def get_asset(self, symbol: str) -> Dict:
        """
        Get detailed info for a single asset.

        Returns tradability, shortability, fractionability, margin requirements, etc.
        """
        return self.portfolio.get_asset(symbol)

    def get_all_assets(
        self,
        status: Optional[str] = None,
        asset_class: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get all assets, optionally filtered.

        Args:
            status: 'active' or 'inactive'
            asset_class: 'us_equity', 'us_option', or 'crypto'
        """
        return self.portfolio.get_all_assets(status=status, asset_class=asset_class)

    # ── Trading ──────────────────────────────────────────────────────

    def buy(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        stop_loss_limit: Optional[float] = None,
        order_class: Optional[str] = None,
        time_in_force: str = 'day',
    ) -> Dict:
        """
        Buy an asset. Order type is inferred from parameters provided.

        Args:
            symbol: Stock symbol or crypto pair
            qty: Number of shares (use qty or notional, not both)
            notional: Dollar amount to spend
            limit_price: Limit order price
            stop_price: Stop trigger price
            trail_price: Dollar offset for trailing stop
            trail_percent: Percent offset for trailing stop
            take_profit: Take profit limit price (exit leg)
            stop_loss: Stop loss trigger price (exit leg)
            stop_loss_limit: Stop loss limit price (omit for market on trigger)
            order_class: 'bracket', 'oco', 'oto'
            time_in_force: 'day', 'gtc', 'ioc', 'fok', 'opg', 'cls'
        """
        return self.trading.buy(
            symbol=symbol, qty=qty, notional=notional,
            limit_price=limit_price, stop_price=stop_price,
            trail_price=trail_price, trail_percent=trail_percent,
            take_profit=take_profit, stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit, order_class=order_class,
            time_in_force=time_in_force,
        )

    def sell(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        stop_loss_limit: Optional[float] = None,
        order_class: Optional[str] = None,
        time_in_force: str = 'day',
    ) -> Dict:
        """
        Sell an asset. Order type is inferred from parameters provided.

        Args:
            symbol: Stock symbol or crypto pair
            qty: Number of shares (use qty or notional, not both)
            notional: Dollar amount to sell
            limit_price: Limit order price
            stop_price: Stop trigger price
            trail_price: Dollar offset for trailing stop
            trail_percent: Percent offset for trailing stop
            take_profit: Take profit limit price (exit leg)
            stop_loss: Stop loss trigger price (exit leg)
            stop_loss_limit: Stop loss limit price (omit for market on trigger)
            order_class: 'bracket', 'oco', 'oto'
            time_in_force: 'day', 'gtc', 'ioc', 'fok', 'opg', 'cls'
        """
        return self.trading.sell(
            symbol=symbol, qty=qty, notional=notional,
            limit_price=limit_price, stop_price=stop_price,
            trail_price=trail_price, trail_percent=trail_percent,
            take_profit=take_profit, stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit, order_class=order_class,
            time_in_force=time_in_force,
        )

    def replace_order(
        self,
        order_id: str,
        qty: Optional[int] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail: Optional[float] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict:
        """
        Modify an existing open order.

        Args:
            order_id: UUID of the order to modify
            qty: New quantity (integer only)
            limit_price: New limit price
            stop_price: New stop trigger price
            trail: New trail value (for trailing stops)
            time_in_force: New time_in_force value
        """
        return self.trading.replace_order(
            order_id=order_id, qty=qty, limit_price=limit_price,
            stop_price=stop_price, trail=trail, time_in_force=time_in_force,
        )

    def close_position(
        self,
        symbol: str,
        qty: Optional[float] = None,
        percentage: Optional[float] = None,
    ) -> Dict:
        """
        Close a position fully or partially.

        Omit both qty and percentage for a full close.

        Args:
            symbol: Ticker symbol
            qty: Number of shares to close (partial)
            percentage: Fraction to close, 0.0–1.0 (e.g., 0.5 = 50%)
        """
        return self.trading.close_position(symbol, qty=qty, percentage=percentage)

    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        return self.trading.close_all_positions(cancel_orders)

    def cancel_order(self, order_id: str) -> None:
        self.trading.cancel_order(order_id)

    def cancel_all_orders(self) -> None:
        self.trading.cancel_all_orders()

    def get_order_by_id(self, order_id: str, nested: bool = True) -> Dict:
        """
        Retrieve a specific order by UUID.

        Args:
            order_id: Order UUID
            nested: If True, include leg details for multi-leg/bracket orders
        """
        return self.trading.get_order_by_id(order_id, nested=nested)

    # ── Options ──────────────────────────────────────────────────────

    def get_options_chain(
        self, underlying: str, expiration: Optional[str] = None,
        limit: Optional[int] = None, return_df: Optional[bool] = None,
    ):
        return self.options.get_options_chain(
            underlying=underlying, expiration=expiration, limit=limit, return_df=return_df,
        )

    def get_option_expirations(
        self, underlying: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[str]:
        return self.options.get_available_dates(underlying=underlying, start=start, end=end)

    def get_option_contracts(
        self, underlying: str, expiration: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        return self.options.get_available_contracts(
            underlying=underlying, expiration=expiration,
            contract_type=contract_type, strike_range=strike_range, limit=limit,
        )

    def buy_option(
        self, symbol: str, qty: int = 1,
        limit_price: Optional[float] = None, time_in_force: str = 'day',
    ) -> Dict:
        return self.trading.buy(symbol=symbol, qty=qty, limit_price=limit_price, time_in_force=time_in_force)

    def sell_option(
        self, symbol: str, qty: int = 1,
        limit_price: Optional[float] = None, time_in_force: str = 'day',
    ) -> Dict:
        return self.trading.sell(symbol=symbol, qty=qty, limit_price=limit_price, time_in_force=time_in_force)

    def exercise_options_position(self, symbol_or_contract_id: str) -> None:
        """
        Exercise a held options position.

        Args:
            symbol_or_contract_id: OSI symbol or contract UUID
        """
        self.trading.exercise_options_position(symbol_or_contract_id)

    def submit_multi_leg_order(
        self,
        legs: List[Dict],
        qty: int,
        limit_price: Optional[float] = None,
        time_in_force: str = 'day',
    ) -> Dict:
        """
        Submit a multi-leg option order (spreads, straddles, iron condors, etc.).

        Args:
            legs: List of leg dicts, each with:
                - symbol: OSI option symbol (required)
                - ratio_qty: Proportional qty relative to parent qty (default 1)
                - side: 'buy' or 'sell' (provide side or position_intent)
                - position_intent: 'buy_to_open', 'sell_to_open', etc.
            qty: Number of contracts for the whole spread
            limit_price: Net debit (positive) or net credit (negative). Omit for market.
            time_in_force: 'day', 'gtc', etc.
        """
        return self.trading.submit_multi_leg_order(
            legs=legs, qty=qty, limit_price=limit_price, time_in_force=time_in_force,
        )

    # ── Option Market Data ─────────────────────────────────────────

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get OHLCV bars for an option contract.

        Args:
            symbol: OSI option symbol (e.g., 'SPY260320C00580000')
            timeframe: '1min', '1h', '1d', '1w', '1m'
            start: Start date/datetime ISO string
            end: End date/datetime ISO string
            limit: Max bars to return
        """
        return self.options.get_option_bars(
            symbol=symbol, timeframe=timeframe, start=start, end=end, limit=limit,
        )

    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get the latest bid/ask quote for an option contract (OSI symbol)."""
        return self.options.get_option_latest_quote(symbol)

    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get a full snapshot (quote + trade + greeks) for an option contract (OSI symbol)."""
        return self.options.get_option_snapshot(symbol)

    # ── Utilities ────────────────────────────────────────────────────

    def is_paper(self) -> bool:
        return self.client.is_paper_trading()
