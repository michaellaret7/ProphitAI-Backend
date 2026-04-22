"""Custom intraday risk model.

Three pre-trade/portfolio-level gates:
  1. Daily drawdown stop — if today's PnL breaches `-max_daily_drawdown_pct`
     of the day's opening equity, flatten everything and refuse new entries
     for the rest of the session.
  2. Gross exposure cap — reject target books whose gross notional exceeds
     `max_gross_exposure` of equity.
  3. End-of-day liquidation — within `exit_minutes_before_close` minutes of
     the close, force all targets to zero.

The model is stateful (tracks day-open equity + halt flag) and should be
checked on every tick before `SetHoldings`.
"""
from datetime import time


class IntradayRiskModel:
    """Pre-trade filter for intraday long/short books."""

    def __init__(
        self,
        max_daily_drawdown_pct: float = 0.02,
        max_gross_exposure: float = 2.0,
        exit_minutes_before_close: int = 15,
        market_close: time = time(16, 0),
    ) -> None:
        self._max_dd = abs(max_daily_drawdown_pct)
        self._max_gross = max_gross_exposure
        self._exit_before_close_min = exit_minutes_before_close
        self._close = market_close

        self._last_day: int | None = None
        self._day_open_equity: float | None = None
        self._halted: bool = False

    def filter_targets(self, algorithm, targets: dict) -> dict:
        """Return a possibly-modified copy of target weights."""

        equity = float(algorithm.Portfolio.TotalPortfolioValue)
        now = algorithm.Time
        day_key = now.toordinal()

        if self._last_day != day_key:
            self._last_day = day_key
            self._day_open_equity = equity
            self._halted = False

        if self._day_open_equity is None or self._day_open_equity <= 0:
            return dict(targets)

        dd = (equity - self._day_open_equity) / self._day_open_equity

        if not self._halted and dd <= -self._max_dd:
            self._halted = True
            algorithm.Log(
                f"[RISK] Daily DD guard tripped at {dd:.2%} "
                f"(threshold -{self._max_dd:.2%}). Flattening + halting."
            )

        close_t = now.replace(
            hour=self._close.hour, minute=self._close.minute, second=0, microsecond=0
        )
        minutes_to_close = (close_t - now).total_seconds() / 60.0

        if self._halted or minutes_to_close <= self._exit_before_close_min:
            return {sym: 0.0 for sym in targets}

        gross = sum(abs(w) for w in targets.values())

        if gross > self._max_gross and gross > 0:
            scale = self._max_gross / gross
            return {sym: w * scale for sym, w in targets.items()}

        return dict(targets)
