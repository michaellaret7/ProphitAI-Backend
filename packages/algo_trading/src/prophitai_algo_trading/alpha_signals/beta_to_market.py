"""Betting-Against-Beta alpha.

Frazzini & Pedersen (2014, JFE "Betting Against Beta") documented that
high-beta stocks underperform on a risk-adjusted basis — leverage-
constrained investors bid up high-beta names, leaving low-beta names
with positive risk-adjusted excess returns. The signal is the cross-
sectional negation of beta against the universe-mean return:

    market_t = mean(return across universe at t)
    beta_i   = cov(return_i, market) / var(market)   over rolling window
    score_i  = median_universe_beta - beta_i

Positive score = below-median beta = long candidate. Distinct from
``LowVolAlpha`` (total vol) and ``IdiosyncraticVolAlpha`` (residual
vol): BAB is purely about *systematic risk loading*. Frazzini-Pedersen
show beta and idio vol are separable empirically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class BetaToMarketAlpha(CrossSectionalAlpha):
    """Cross-sectional negated beta against the universe-mean return.

    Args:
        lookback_days: Window over which beta is estimated (default 60).
        hold_days: Informational ``close_time`` horizon.
        min_universe_size: Universe-size floor for the median.
    """

    name = "beta_to_market"

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

        beta_by_symbol: dict[str, float] = {}

        for symbol in return_panel.columns:
            stock_returns = return_panel[symbol]

            cov = float(stock_returns.cov(market_return))
            beta = cov / market_var

            if not np.isfinite(beta):
                continue

            beta_by_symbol[symbol] = beta

        if len(beta_by_symbol) < self._min_universe:
            return None

        median_beta = float(np.median(list(beta_by_symbol.values())))

        return {"beta": beta_by_symbol, "median": median_beta}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        beta_by_symbol: dict[str, float] = stats["beta"]
        median_beta: float = stats["median"]

        beta = beta_by_symbol.get(symbol)

        if beta is None:
            return None

        return median_beta - beta

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional BAB across the panel.

        Per bar: compute the universe-mean return as the market proxy,
        run a rolling beta per ticker via the closed-form
        ``cov(ret, mkt) / var(mkt)``, then row-rank vs. universe median.
        """
        returns = panel.close.pct_change()

        market = returns.mean(axis=1)

        market_var = market.rolling(self._window).var(ddof=1)

        # Reason: rolling cov via E[ret*mkt] - E[ret]E[mkt].
        ret_mkt = returns.mul(market, axis=0)

        e_ret = returns.rolling(self._window).mean()
        e_mkt = market.rolling(self._window).mean()
        e_ret_mkt = ret_mkt.rolling(self._window).mean()

        cov = e_ret_mkt.sub(e_ret.mul(e_mkt, axis=0), axis=0)

        beta = cov.div(market_var.where(market_var > 0.0), axis=0)

        valid_count = beta.count(axis=1)
        median_beta = beta.median(axis=1)

        score = beta.rsub(median_beta, axis=0)

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
