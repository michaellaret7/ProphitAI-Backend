"""Unified Alpaca interface — one entry point that fans out to sub-services.

``Alpaca`` composes ``AlpacaClient`` + ``AlpacaTrading`` + ``AlpacaPortfolio``
+ ``OptionsService``. Most callers only need this class; reach for the
sub-services directly (``alpaca.trading`` / ``alpaca.portfolio`` /
``alpaca.options``) for less-common operations.
"""

from __future__ import annotations

from prophitai_algo_trading.brokers.alpaca.account import AlpacaPortfolio
from prophitai_algo_trading.brokers.alpaca.client import AlpacaClient
from prophitai_algo_trading.brokers.alpaca.options import OptionsService
from prophitai_algo_trading.brokers.alpaca.trading import AlpacaTrading
from prophitai_algo_trading.brokers.snapshots import BrokerStartupSnapshot


class Alpaca:
    """Unified interface for all Alpaca operations.

    Usage::

        alpaca = Alpaca()  # Uses env vars for credentials
        alpaca = Alpaca(api_key="...", secret_key="...", paper=True)

        alpaca.buy("AAPL", qty=10)
        alpaca.sell("AAPL", qty=10, trail_percent=2.0)
        alpaca.buy(
            "AAPL", qty=10, take_profit=160, stop_loss=140,
            order_class="bracket",
        )

        alpaca.get_portfolio_history(period="1M", timeframe="1D")
        alpaca.get_asset("AAPL")

        # Direct sub-service access for less-common ops
        alpaca.trading.close_all_positions()
        alpaca.options.get_options_chain("SPY")
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
        options_feed: str = "indicative",
    ):
        self.client = AlpacaClient(api_key=api_key, secret_key=secret_key, paper=paper)
        self.trading = AlpacaTrading(self.client.get_client())
        self.portfolio = AlpacaPortfolio(self.client.get_client())
        self.options = OptionsService(self.client, feed=options_feed)

    #     ================================
    # --> Startup hydration
    #     ================================

    def get_startup_snapshot(self) -> BrokerStartupSnapshot:
        """Fetch a complete startup snapshot for live engine hydration."""
        return self.portfolio.get_startup_snapshot()

    #     ================================
    # --> Account & portfolio
    #     ================================

    def get_account(self) -> dict:
        return self.portfolio.get_account()

    def get_buying_power(self) -> float:
        return self.portfolio.get_account()["buying_power"]

    def get_cash(self) -> float:
        return self.portfolio.get_account()["cash"]

    def get_equity(self) -> float:
        return self.portfolio.get_account()["equity"]

    def get_positions(self) -> list[dict]:
        return self.portfolio.get_positions()

    def get_position(self, symbol: str) -> dict | None:
        return self.portfolio.get_position(symbol)

    def get_orders(self, status: str = "open") -> list[dict]:
        return self.portfolio.get_orders(status)

    def get_portfolio_history(
        self,
        period: str | None = None,
        timeframe: str | None = None,
        extended_hours: bool | None = None,
    ) -> dict:
        """Historical portfolio equity / P&L over ``period`` at ``timeframe``."""
        return self.portfolio.get_portfolio_history(
            period=period,
            timeframe=timeframe,
            extended_hours=extended_hours,
        )

    #     ================================
    # --> Assets
    #     ================================

    def get_asset(self, symbol: str) -> dict:
        return self.portfolio.get_asset(symbol)

    def get_all_assets(
        self,
        status: str | None = None,
        asset_class: str | None = None,
    ) -> list[dict]:
        """Every tradeable asset; optional ``status`` / ``asset_class`` filters."""
        return self.portfolio.get_all_assets(status=status, asset_class=asset_class)

    #     ================================
    # --> Trading
    #     ================================

    def buy(self, symbol: str, **kwargs) -> dict:
        """Buy ``symbol``. See ``AlpacaTrading._submit_order`` for kwargs."""
        return self.trading.buy(symbol=symbol, **kwargs)

    def sell(self, symbol: str, **kwargs) -> dict:
        """Sell ``symbol``. See ``AlpacaTrading._submit_order`` for kwargs."""
        return self.trading.sell(symbol=symbol, **kwargs)

    def replace_order(
        self,
        order_id: str,
        qty: int | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail: float | None = None,
        time_in_force: str | None = None,
    ) -> dict:
        return self.trading.replace_order(
            order_id=order_id,
            qty=qty,
            limit_price=limit_price,
            stop_price=stop_price,
            trail=trail,
            time_in_force=time_in_force,
        )

    def close_position(
        self,
        symbol: str,
        qty: float | None = None,
        percentage: float | None = None,
    ) -> dict:
        return self.trading.close_position(symbol, qty=qty, percentage=percentage)

    def close_all_positions(self, cancel_orders: bool = True) -> list[dict]:
        return self.trading.close_all_positions(cancel_orders)

    def cancel_order(self, order_id: str) -> None:
        self.trading.cancel_order(order_id)

    def cancel_all_orders(self) -> None:
        self.trading.cancel_all_orders()

    def get_order_by_id(self, order_id: str, nested: bool = True) -> dict:
        return self.trading.get_order_by_id(order_id, nested=nested)

    #     ================================
    # --> Options
    #     ================================

    def get_options_chain(
        self,
        underlying: str,
        expiration: str | None = None,
        limit: int | None = None,
        return_df: bool | None = None,
    ):
        return self.options.get_options_chain(
            underlying=underlying,
            expiration=expiration,
            limit=limit,
            return_df=return_df,
        )

    def get_option_expirations(
        self,
        underlying: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[str]:
        return self.options.get_available_dates(
            underlying=underlying, start=start, end=end,
        )

    def get_option_contracts(
        self,
        underlying: str,
        expiration: str | None = None,
        contract_type: str | None = None,
        strike_range: tuple[float, float] | None = None,
        limit: int | None = None,
    ) -> list[str]:
        return self.options.get_available_contracts(
            underlying=underlying,
            expiration=expiration,
            contract_type=contract_type,
            strike_range=strike_range,
            limit=limit,
        )

    def buy_option(
        self,
        symbol: str,
        qty: int = 1,
        limit_price: float | None = None,
        time_in_force: str = "day",
    ) -> dict:
        return self.trading.buy(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            time_in_force=time_in_force,
        )

    def sell_option(
        self,
        symbol: str,
        qty: int = 1,
        limit_price: float | None = None,
        time_in_force: str = "day",
    ) -> dict:
        return self.trading.sell(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            time_in_force=time_in_force,
        )

    def exercise_options_position(self, symbol_or_contract_id: str) -> None:
        """Exercise a held options position (OSI symbol or contract UUID)."""
        self.trading.exercise_options_position(symbol_or_contract_id)

    def submit_multi_leg_order(
        self,
        legs: list[dict],
        qty: int,
        limit_price: float | None = None,
        time_in_force: str = "day",
    ) -> dict:
        """Submit a multi-leg option order (spreads, straddles, condors, ...)."""
        return self.trading.submit_multi_leg_order(
            legs=legs,
            qty=qty,
            limit_price=limit_price,
            time_in_force=time_in_force,
        )

    #     ================================
    # --> Option market data
    #     ================================

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """OHLCV bars for an OSI option contract."""
        return self.options.get_option_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
        )

    def get_option_latest_quote(self, symbol: str) -> dict:
        return self.options.get_option_latest_quote(symbol)

    def get_option_snapshot(self, symbol: str) -> dict:
        return self.options.get_option_snapshot(symbol)

    #     ================================
    # --> Utilities
    #     ================================

    def is_paper(self) -> bool:
        return self.client.is_paper_trading()
