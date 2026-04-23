"""Three novel alphas for the quality-adjusted cross-sectional trend strategy.

Distinct from the five built-in alphas in prophitai_algo_trading.alphas:

    RiskAdjustedMomentumAlpha   Sharpe-style momentum (return / vol)
    PriceAccelerationAlpha      Is recent 30-day return > prior 30-day return?
    VolatilityContractionAlpha  Cross-sec vol compression detector (regime)

Thesis: medium-term price trends (3 months) outperform naive 12-1
momentum when adjusted for noise (vol) and regime (vol compression).
Directional per-symbol for the first two, cross-sectional median split
for the third (same structure as the built-in LowVolAlpha).
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from prophitai_algo_trading.framework import AlgorithmContext, Insight


#     ================================
# --> Risk-adjusted momentum
#     ================================

class RiskAdjustedMomentumAlpha:
    """63-day log-return mean divided by log-return std.

    Equivalent to the Sharpe ratio of daily returns over the window
    (without annualization — annualization is a constant, so it doesn't
    change cross-sectional ranking). Penalizes noisy runups, rewards
    steady climbers. The classic "frog-in-the-pan" quality signal.

    Args:
        lookback_days: Window over which mean + std of daily log returns
            is computed. Default 63 (~3 months).
        hold_days: Informational ``close_time`` horizon.
    """

    name = "risk_adj_momentum"

    def __init__(self, lookback_days: int = 63, hold_days: int = 5):
        self._lookback_days = lookback_days
        self._hold_days = hold_days
        self.lookback = lookback_days + 1

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        insights: list[Insight] = []

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            window = df["close"].iloc[-self.lookback:]

            log_returns = np.log(window).diff().dropna()

            if len(log_returns) < 2:
                continue

            mean_r = float(log_returns.mean())
            std_r = float(log_returns.std())

            if std_r <= 0.0 or not np.isfinite(std_r):
                continue

            # Reason: Sharpe-style ratio — penalizes noisy rallies.
            sharpe_like = mean_r / std_r

            direction = 1 if sharpe_like > 0.0 else -1 if sharpe_like < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(sharpe_like),
                source_alpha=self.name,
            ))

        return insights


#     ================================
# --> Price acceleration
#     ================================

class PriceAccelerationAlpha:
    """Difference between recent-30-day return and prior-30-day return.

    Compares two equal-length return windows:
        r_recent  = P_t / P_{t-30} - 1     (last 30 days)
        r_earlier = P_{t-30} / P_{t-60} - 1 (the 30 days before that)
        acceleration = r_recent - r_earlier

    Positive acceleration = momentum is speeding up → long.
    Negative = decelerating or reversing → short.

    Args:
        fast_days: Length of the recent window (default 30 trading days).
        slow_days: Twice the fast window — needed for the earlier comp
            (default 60).
        hold_days: Informational ``close_time`` horizon.
    """

    name = "price_acceleration"

    def __init__(
        self,
        fast_days: int = 30,
        slow_days: int = 60,
        hold_days: int = 5,
    ):
        if slow_days < 2 * fast_days:
            raise ValueError("slow_days must be >= 2 * fast_days")

        self._fast = fast_days
        self._slow = slow_days
        self._hold_days = hold_days
        self.lookback = slow_days + 1

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        insights: list[Insight] = []

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]

            p_now = float(closes.iloc[-1])
            p_mid = float(closes.iloc[-(self._fast + 1)])
            p_old = float(closes.iloc[-(self._slow + 1)])

            if p_now <= 0.0 or p_mid <= 0.0 or p_old <= 0.0:
                continue

            r_recent = (p_now / p_mid) - 1.0
            r_earlier = (p_mid / p_old) - 1.0

            acceleration = r_recent - r_earlier

            direction = 1 if acceleration > 0.0 else -1 if acceleration < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(acceleration),
                source_alpha=self.name,
            ))

        return insights


#     ================================
# --> Volatility contraction (cross-sectional)
#     ================================

class VolatilityContractionAlpha:
    """Cross-sectional median split on the ratio of short vol to long vol.

        ratio = std(log_returns, 20d) / std(log_returns, 60d)

    Low ratio => recent vol has contracted below trailing — often a
    coiling pattern that precedes breakouts. Long bias.
    High ratio => vol expansion in progress — often late in a move.
    Short bias.

    Direction is assigned via median split across the ready universe so
    the alpha is always directionally balanced.

    Args:
        recent_days: Short vol window (default 20).
        long_days: Long vol window (default 60).
        hold_days: ``close_time`` horizon.
        min_universe_size: Minimum ready symbols before any insights
            are emitted.
    """

    name = "vol_contraction"

    def __init__(
        self,
        recent_days: int = 20,
        long_days: int = 60,
        hold_days: int = 10,
        min_universe_size: int = 3,
    ):
        if recent_days >= long_days:
            raise ValueError("recent_days must be < long_days")

        self._recent = recent_days
        self._long = long_days
        self._hold_days = hold_days
        self._min_universe = min_universe_size
        self.lookback = long_days + 1

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        ratios: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            log_returns = np.log(df["close"]).diff().dropna()

            if len(log_returns) < self._long:
                continue

            recent_vol = float(log_returns.iloc[-self._recent:].std())
            long_vol = float(log_returns.iloc[-self._long:].std())

            if recent_vol <= 0.0 or long_vol <= 0.0:
                continue

            ratio = recent_vol / long_vol

            if not np.isfinite(ratio):
                continue

            ratios[symbol] = ratio

        if len(ratios) < self._min_universe:
            return []

        median_ratio = float(np.median(list(ratios.values())))

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        insights: list[Insight] = []

        for symbol, ratio in ratios.items():
            # Reason: low-ratio (contracting) names go long; high-ratio
            # (expanded) go short — positive distance means below-median.
            distance = median_ratio - ratio

            direction = 1 if distance > 0.0 else -1 if distance < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(distance),
                source_alpha=self.name,
            ))

        return insights
