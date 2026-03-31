"""Portfolio tracker — handles position tracking, P&L, and optional broker routing.

Single class replaces the former BaseExecutor → TrackingExecutor → SimulatedExecutor /
BrokerExecutor hierarchy. Uses CostModel for consistent transaction cost handling.
"""

import math
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.models import Direction, PositionState, PortfolioContext, Trade
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.sizing import BasePositionSizer


class PortfolioTracker:
    """Portfolio tracker with full position, trade, and equity tracking.

    Args:
        initial_capital: Starting cash balance.
        sizer: Position sizing strategy.
        cost_model: Transaction cost model (replaces raw commission_pct).
        broker: Optional broker instance (e.g. Alpaca) for live/paper trading.
    """

    def __init__(
        self,
        initial_capital: float,
        sizer: BasePositionSizer,
        cost_model: CostModel | None = None,
        broker=None,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self._cost_model = cost_model or CostModel()
        self._sizer = sizer
        self._broker = broker
        self._positions: dict[str, PositionState] = {}
        self._equity_history: list[dict] = []
        self._trades: list[Trade] = []
        self._latest_prices: dict[str, float] = {}
        self._peak_equity = initial_capital

    # ================================
    # --> Hydration (live startup only)
    # ================================

    def seed_cash(self, cash: float) -> None:
        """Override cash with the broker's reported cash balance.

        Called during live startup hydration after the tracker is constructed
        with initial_capital=broker_equity. Backtests must never call this.
        """
        self.cash = cash

    def seed_position(
        self,
        symbol: str,
        shares: float,
        direction: Direction,
        entry_price: float,
        entry_date: datetime,
        entry_commission: float = 0.0,
    ) -> None:
        """Inject a broker position into the tracker without executing a trade.

        Called during live startup hydration to restore positions that already
        exist on the broker. Does not route orders or deduct cash — the broker
        already holds these positions.
        """
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=direction,
            entry_price=entry_price,
            entry_date=entry_date,
            entry_commission=entry_commission,
        )

    def seed_latest_prices(self, prices: dict[str, float]) -> None:
        """Bulk-set latest prices from warmup data during live hydration."""
        self._latest_prices.update(prices)

    # ================================
    # --> Helper funcs
    # ================================

    def _mark_to_market(self, prices: dict[str, float] | None = None) -> float:
        """Compute total position value at current market prices.

        Args:
            prices: Current market prices keyed by symbol. When provided,
                positions are marked-to-market; otherwise entry prices are used.

        Returns:
            Total position value (can be negative for underwater shorts).
        """
        position_value = 0.0
        for sym, pos in self._positions.items():
            current_price = (prices or {}).get(
                sym, self._latest_prices.get(sym, pos.entry_price),
            )
            if pos.direction == Direction.LONG:
                position_value += pos.shares * current_price
            else:
                position_value += pos.shares * (pos.entry_price - current_price)
        return position_value

    def _compute_exposures(
        self,
        prices: dict[str, float] | None = None,
    ) -> tuple[float, float, float, float]:
        """Return long, short, gross, and net exposure using live prices."""
        long_exposure = 0.0
        short_exposure = 0.0

        for sym, pos in self._positions.items():
            current_price = (prices or {}).get(
                sym, self._latest_prices.get(sym, pos.entry_price),
            )
            notional = pos.shares * current_price
            if pos.direction == Direction.LONG:
                long_exposure += notional
            else:
                short_exposure += notional

        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        return long_exposure, short_exposure, gross_exposure, net_exposure

    def build_portfolio_context(
        self,
        prices: dict[str, float] | None = None,
        timestamp: datetime | None = None,
    ) -> PortfolioContext:
        """Build a PortfolioContext snapshot for sizing and risk checks.

        Args:
            prices: Current market prices keyed by symbol.
        """
        position_value = self._mark_to_market(prices)
        equity = self.cash + position_value
        self._peak_equity = max(self._peak_equity, equity)
        long_exposure, short_exposure, gross_exposure, net_exposure = (
            self._compute_exposures(prices)
        )

        return PortfolioContext(
            equity=equity,
            cash=self.cash,
            positions=dict(self._positions),
            latest_prices={**self._latest_prices, **(prices or {})},
            open_position_count=len(self._positions),
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            peak_equity=self._peak_equity,
            drawdown_pct=(
                max(self._peak_equity - equity, 0.0) / self._peak_equity
                if self._peak_equity > 0
                else 0.0
            ),
            timestamp=timestamp,
        )

    def get_position(self, symbol: str) -> PositionState | None:
        """Return the open position for a symbol, or None if flat."""
        return self._positions.get(symbol)

    def update_market_prices(self, prices: dict[str, float]) -> None:
        """Merge the latest known market prices into the tracker state."""
        self._latest_prices.update(prices)

    @property
    def open_position_count(self) -> int:
        """Number of currently open positions."""
        return len(self._positions)

    @property
    def has_open_positions(self) -> bool:
        """Whether any positions are currently open."""
        return bool(self._positions)

    @property
    def open_symbols(self) -> list[str]:
        """Symbols with currently open positions."""
        return list(self._positions.keys())

    @property
    def last_trade_pnl(self) -> float:
        """P&L of the most recent closed trade, or 0.0 if no trades yet."""
        return self._trades[-1].pnl if self._trades else 0.0

    def get_total_equity(self, prices: dict[str, float] | None = None) -> float:
        """Current total equity (cash + position value)."""
        return self.cash + self._mark_to_market(prices)

    def execute_instruction(self, instruction: dict, symbol: str) -> None:
        """Route a trade instruction from PositionTracker to the right method.

        Args:
            instruction: Dict with 'reason', 'price', 'timestamp' keys.
            symbol: Ticker symbol for the trade.
        """
        reason = instruction["reason"]
        price = instruction["price"]
        timestamp = instruction["timestamp"]
        target_shares = instruction.get("target_shares")

        if reason == "open_long":
            self.open_long(symbol, price, timestamp, shares=target_shares)
        elif reason == "close_long":
            self.close_position(symbol, price, timestamp)
        elif reason == "open_short":
            self.open_short(symbol, price, timestamp, shares=target_shares)
        elif reason == "close_short":
            self.close_position(symbol, price, timestamp)
        else:
            raise ValueError(f"Unknown trade reason: {reason}")

    def open_long(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        shares: float | None = None,
    ) -> None:
        """Open a long position using an explicit share target or the injected sizer."""
        context = self.build_portfolio_context(prices={symbol: price}, timestamp=timestamp)
        shares = (
            shares if shares is not None
            else self._sizer.calculate_shares(symbol, price, context)
        )
        if pd.isna(shares) or shares <= 0:
            return
        commission = self._cost_model.cost_for_trade(price, shares)

        if self._broker:
            self._broker.buy(symbol, qty=shares)
            print(f"[OPEN LONG] {symbol}  shares={shares}  price={price:.2f}")

        self._latest_prices[symbol] = price
        self.cash -= (shares * price + commission)
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=Direction.LONG,
            entry_price=price,
            entry_date=timestamp,
            entry_commission=commission,
        )

    def open_short(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        shares: float | None = None,
    ) -> None:
        """Open a short position using an explicit share target or the injected sizer."""
        context = self.build_portfolio_context(prices={symbol: price}, timestamp=timestamp)
        # Reason: brokers do not allow fractional short selling
        raw_shares = (
            shares if shares is not None
            else self._sizer.calculate_shares(symbol, price, context)
        )
        shares = math.floor(raw_shares)
        if shares < 1:
            return
        commission = self._cost_model.cost_for_trade(price, shares)

        if self._broker:
            self._broker.sell(symbol, qty=shares)
            print(f"[OPEN SHORT] {symbol}  shares={shares}  price={price:.2f}")

        # Reason: for shorts, cash is retained as margin; only commission is deducted on entry.
        self._latest_prices[symbol] = price
        self.cash -= commission
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=Direction.SHORT,
            entry_price=price,
            entry_date=timestamp,
            entry_commission=commission,
        )

    def close_position(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Close a position and log the trade."""
        pos = self._positions.get(symbol)
        if pos is None:
            return

        if self._broker:
            self._broker.close_position(symbol)
            print(f"[CLOSE] {symbol}  price={price:.2f}  direction={pos.direction.value}")

        self._latest_prices[symbol] = price
        exit_commission = self._cost_model.cost_for_trade(price, pos.shares)
        total_commission = pos.entry_commission + exit_commission

        if pos.direction == Direction.LONG:
            proceeds = pos.shares * price - exit_commission
            self.cash += proceeds
            pnl = (price - pos.entry_price) * pos.shares - total_commission
        else:
            # Reason: short P&L is (entry - exit) * shares. Cash already holds margin,
            # so add back raw P&L plus the entry commission that was deducted on open.
            pnl = (pos.entry_price - price) * pos.shares - total_commission
            self.cash += pnl + pos.entry_commission

        entry_value = pos.shares * pos.entry_price
        return_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0.0

        self._trades.append(Trade(
            symbol=symbol,
            entry_date=pos.entry_date,
            exit_date=timestamp,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=price,
            shares=pos.shares,
            pnl=round(pnl, 2),
            return_pct=round(return_pct, 2),
        ))

        del self._positions[symbol]

    def record_equity(self, timestamp: datetime, prices: dict[str, float]) -> None:
        """Snapshot current portfolio equity using live prices for open positions."""
        self.update_market_prices(prices)
        position_value = self._mark_to_market(prices)
        equity = self.cash + position_value
        self._peak_equity = max(self._peak_equity, equity)

        self._equity_history.append({
            "timestamp": timestamp,
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "position_value": round(position_value, 2),
        })

    def get_equity_curve(self) -> pd.DataFrame:
        """Return equity history as a DataFrame indexed by timestamp."""
        if not self._equity_history:
            return pd.DataFrame(columns=["equity", "cash", "position_value"])

        df = pd.DataFrame(self._equity_history)
        df = df.set_index("timestamp")
        return df

    def get_trades_df(self) -> pd.DataFrame:
        """Return trade log as a DataFrame."""
        if not self._trades:
            return pd.DataFrame(columns=[
                "symbol", "entry_date", "exit_date", "direction", "entry_price",
                "exit_price", "shares", "pnl", "return_pct",
            ])

        return pd.DataFrame([vars(t) for t in self._trades])
