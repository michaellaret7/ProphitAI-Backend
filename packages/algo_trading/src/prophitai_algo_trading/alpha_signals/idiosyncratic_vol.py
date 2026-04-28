"""Idiosyncratic volatility alpha.

Ang, Hodrick, Xing & Zhang (2006, J. Finance "The Cross-Section of
Volatility and Expected Returns") showed the low-IVOL anomaly: stocks
with low *idiosyncratic* (residual) volatility outperform after
controlling for market exposure.

The signal regresses each ticker's daily returns on the universe-mean
return (a proxy for the market factor when fundamentals aren't
available), then takes the std-dev of the residuals as IVOL.

    market_return_t = mean(return_t across universe)
    ε_i,t           = ret_i,t - α_i - β_i * market_return_t
    IVOL_i,t        = std(ε_i over rolling window)
    score_i         = median_universe_IVOL - IVOL_i

Positive score = below-median IVOL = long candidate. Distinct from
``LowVolAlpha`` because that uses *total* return std-dev (mixing
market and idio components); IVOL strips out market beta first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class IdiosyncraticVolAlpha(CrossSectionalAlpha):
    """Cross-sectional low-IVOL score (residual std-dev after market).

    Args:
        lookback_days: Window over which IVOL is measured (default 60).
        hold_days: Informational ``close_time`` horizon.
        min_universe_size: Universe-size floor for the median.
    """

    name = "idio_vol"

    def __init__(
        self,
        lookback_days: int = 60,
        hold_days: int = 21,
        min_universe_size: int = 10,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        # Reason: assemble {symbol: returns} aligned on the latest window
        # so we can compute a market series and per-stock IVOL together.
        ready: dict[str, pd.Series] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            returns = df["close"].pct_change().iloc[-self._window:]

            if returns.isna().any():
                continue

            ready[symbol] = returns

        if len(ready) < self._min_universe:
            return None

        return_panel = pd.DataFrame(ready)

        market_return = return_panel.mean(axis=1)

        market_var = float(market_return.var(ddof=1))

        if market_var <= 0.0:
            return None

        ivol_by_symbol: dict[str, float] = {}

        for symbol in return_panel.columns:
            stock_returns = return_panel[symbol]

            cov = float(stock_returns.cov(market_return))
            beta = cov / market_var

            residuals = stock_returns - beta * market_return

            ivol = float(residuals.std(ddof=1))

            if not np.isfinite(ivol) or ivol <= 0.0:
                continue

            ivol_by_symbol[symbol] = ivol

        if len(ivol_by_symbol) < self._min_universe:
            return None

        median_ivol = float(np.median(list(ivol_by_symbol.values())))

        return {"ivol": ivol_by_symbol, "median": median_ivol}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        ivol_by_symbol: dict[str, float] = stats["ivol"]
        median_ivol: float = stats["median"]

        ivol = ivol_by_symbol.get(symbol)

        if ivol is None:
            return None

        return median_ivol - ivol

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional IVOL.

        Per bar: compute the universe-mean return as the market proxy,
        run a rolling beta per ticker via the closed-form
        ``cov(ret, mkt) / var(mkt)``, take the std-dev of residuals
        over the window, then row-rank vs. universe median.
        """
        returns = panel.close.pct_change()

        market = returns.mean(axis=1)

        market_var = market.rolling(self._window).var(ddof=1)

        # Reason: rolling cov per ticker via E[ret*mkt] - E[ret]E[mkt].
        ret_mkt = returns.mul(market, axis=0)

        e_ret = returns.rolling(self._window).mean()
        e_mkt = market.rolling(self._window).mean()
        e_ret_mkt = ret_mkt.rolling(self._window).mean()

        cov = e_ret_mkt.sub(e_ret.mul(e_mkt, axis=0), axis=0)

        beta = cov.div(market_var.where(market_var > 0.0), axis=0)

        # Reason: residuals = ret - beta * mkt; row-aligned multiplication.
        beta_mkt = beta.mul(market, axis=0)
        residuals = returns - beta_mkt

        ivol = residuals.rolling(self._window).std(ddof=1)
        ivol = ivol.where(ivol > 0.0)

        valid_count = ivol.count(axis=1)
        median_ivol = ivol.median(axis=1)

        score = ivol.rsub(median_ivol, axis=0)

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
