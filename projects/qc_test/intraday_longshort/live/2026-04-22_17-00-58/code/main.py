"""IntradayLongShortEquity — Lean showcase intraday strategy.

Long/short cross-sectional mean-reversion on 15-minute bars of a curated
universe of liquid US equities. Everything — prices, indicators, portfolio
construction, risk — is custom and reads from ProphitAI's own data.

Logic (per 15-min bar during regular trading hours):
  1. Update session-level custom indicators (VWAP deviation + return z-score).
  2. Every REBALANCE_EVERY_N_BARS bars, build a composite score per stock:
       composite = 0.6 * vwap_deviation + 0.4 * normalized_return_zscore
     Higher composite = more overbought intraday.
  3. DollarNeutralLongShortConstruction picks the bottom quintile long,
     top quintile short, equal weight, dollar-neutral, gross 1.8x.
  4. IntradayRiskModel enforces:
       - Daily DD stop at -2% of day-open equity
       - Gross exposure cap at 2.0x
       - Flatten all positions 15 min before close.

No QuantConnect data is used — all prices come from ProphitAI's DB via the
ProphitAI15MinBar custom PythonData class.
"""
from datetime import time

from AlgorithmImports import PortfolioTarget, QCAlgorithm, Resolution

from custom_data import ProphitAI15MinBar
from custom_indicators import SessionReturnZScore, SessionVWAPDeviation
from custom_portfolio import DollarNeutralLongShortConstruction
from custom_risk import IntradayRiskModel
from universe import UNIVERSE


REBALANCE_EVERY_N_BARS = 2
SESSION_START = time(9, 30)
SESSION_END = time(16, 0)


class IntradayLongShortEquity(QCAlgorithm):

    def initialize(self) -> None:
        self.set_start_date(2024, 6, 3)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1_000_000)

        # Reason: custom PythonData drives signals (from ProphitAI DB).
        # In live mode we also need a real Equity subscription so Alpaca can
        # route orders by actual ticker symbol.
        self._data_symbols = {}  # ticker -> custom data symbol (signals)
        self._symbols = {}       # ticker -> tradeable symbol (equity in live, custom in backtest)
        self._vwap_devs = {}
        self._return_zs = {}
        self._latest_bars = {}

        trade_on_equity = self.live_mode

        for ticker in UNIVERSE:
            data_symbol = self.add_data(
                ProphitAI15MinBar, ticker, Resolution.MINUTE
            ).symbol

            self._data_symbols[ticker] = data_symbol

            if trade_on_equity:
                equity_symbol = self.add_equity(
                    ticker, Resolution.MINUTE, extended_market_hours=False
                ).symbol
                self._symbols[ticker] = equity_symbol
            else:
                self._symbols[ticker] = data_symbol

            self._vwap_devs[ticker] = SessionVWAPDeviation()
            self._return_zs[ticker] = SessionReturnZScore(lookback_sessions=20)

        benchmark_symbol = next(iter(self._symbols.values()))
        self.set_benchmark(benchmark_symbol)

        self._portfolio_builder = DollarNeutralLongShortConstruction(
            gross_exposure=1.8,
            per_position_cap=0.10,
            long_short_quantile=0.2,
        )

        self._risk = IntradayRiskModel(
            max_daily_drawdown_pct=0.02,
            max_gross_exposure=2.0,
            exit_minutes_before_close=15,
            market_close=SESSION_END,
        )

        self._bars_this_session = 0
        self._last_session_day: int | None = None

    def on_data(self, data) -> None:
        now = self.time
        now_t = now.time()

        if now_t < SESSION_START or now_t > SESSION_END:
            return

        day_key = now.toordinal()

        if self._last_session_day != day_key:
            self._last_session_day = day_key
            self._bars_this_session = 0

        any_update = False

        # Reason: signals always come from our custom ProphitAI bars,
        # regardless of live vs backtest, so we read off _data_symbols.
        for ticker, data_symbol in self._data_symbols.items():
            if not data.contains_key(data_symbol):
                continue

            bar = data[data_symbol]

            if bar is None:
                continue

            any_update = True
            self._latest_bars[ticker] = bar

            self._vwap_devs[ticker].update(
                bar.end_time,
                float(bar["high"]),
                float(bar["low"]),
                float(bar["close"]),
                float(bar["volume"]),
            )
            self._return_zs[ticker].update(
                bar.end_time, float(bar["open"]), float(bar["close"])
            )

        if not any_update:
            return

        self._bars_this_session += 1

        if self._bars_this_session % REBALANCE_EVERY_N_BARS != 0:
            return

        scores = self._composite_scores()

        if len(scores) < 6:
            return

        target_weights = self._portfolio_builder.build(scores)

        final_weights = self._risk.filter_targets(self, target_weights)

        self._apply_targets(final_weights)

    #     ================================
    # --> Internal helpers
    #     ================================

    def _composite_scores(self) -> dict:
        scores: dict = {}

        for ticker, symbol in self._symbols.items():
            vd = self._vwap_devs[ticker]
            rz = self._return_zs[ticker]

            if not vd.is_ready:
                continue

            z_part = rz.value if rz.is_ready else 0.0

            composite = 0.6 * vd.value + 0.4 * (z_part / 5.0)

            scores[symbol] = composite

        return scores

    def _apply_targets(self, weights: dict) -> None:
        for symbol in list(self.portfolio.keys()):
            if self.portfolio[symbol].invested and symbol not in weights:
                self.set_holdings(symbol, 0)

        for symbol, w in weights.items():
            current = self.portfolio[symbol].holdings_value / max(
                self.portfolio.total_portfolio_value, 1e-9
            )

            if abs(w - current) > 0.01:
                self.set_holdings(symbol, w)

    def on_end_of_day(self, symbol) -> None:
        if symbol != next(iter(self._symbols.values())):
            return

        invested = sum(
            1 for s in self._symbols.values() if self.portfolio[s].invested
        )

        if invested > 0:
            self.debug(
                f"EOD {self.time.date()}: {invested} positions still open — "
                f"liquidating."
            )

            for s in self._symbols.values():
                if self.portfolio[s].invested:
                    self.liquidate(s)
