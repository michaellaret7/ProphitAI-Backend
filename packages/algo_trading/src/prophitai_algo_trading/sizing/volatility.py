"""Volatility-based sizers: VolatilityTarget, InverseVolatility."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.sizing.base import BaseSizer, SizingInput


def _trailing_vol(df: pd.DataFrame, lookback: int) -> float | None:
    """Realized (close-to-close log-return std) over the last ``lookback`` bars."""
    if len(df) < lookback + 1:
        return None

    close = df["close"].iloc[-(lookback + 1):]
    log_ret = np.log(close).diff().dropna()

    if log_ret.empty:
        return None

    value = float(log_ret.std())

    if not np.isfinite(value) or value <= 0:
        return None

    return value


class VolatilityTargetSizer(BaseSizer):
    """Size each position to target a constant volatility contribution.

    Shares = (equity * target_vol_annual / sqrt(annualization)) / (price * realized_vol).

    Args:
        target_vol_annual: Target annualized volatility per position (0.15 = 15%).
        annualization: Bars per year for the data frequency
            (252 daily, 252*78 for 5-min bars, etc.).
        lookback: Bars used to estimate realized vol.
        cost_model: Transaction costs.
    """

    def __init__(
        self,
        target_vol_annual: float = 0.15,
        annualization: float = 252.0,
        lookback: int = 20,
        cost_model: CostModel | None = None,
    ):
        super().__init__(cost_model)
        self.target_vol_annual = target_vol_annual
        self.annualization = annualization
        self.lookback = lookback

    def size(self, request: SizingInput) -> float:
        vol = _trailing_vol(request.df, self.lookback)

        if vol is None:
            return 0.0

        annualized_vol = vol * np.sqrt(self.annualization)

        if annualized_vol <= 0:
            return 0.0

        target_notional = request.equity * (self.target_vol_annual / annualized_vol)

        if request.direction == 1:
            target_notional = min(target_notional, request.cash)

        return self.cost_model.max_shares(request.price, target_notional)


class InverseVolatilitySizer(BaseSizer):
    """Size inversely proportional to volatility — higher vol gets less capital.

    Uses a base allocation (``pct`` of equity) divided by a normalized vol.

    Args:
        base_pct: Base allocation per trade before vol scaling.
        target_vol: Vol level at which the sizer allocates exactly ``base_pct``.
        lookback: Bars used to estimate realized vol.
        cost_model: Transaction costs.
    """

    def __init__(
        self,
        base_pct: float = 0.10,
        target_vol: float = 0.02,
        lookback: int = 20,
        cost_model: CostModel | None = None,
    ):
        super().__init__(cost_model)
        self.base_pct = base_pct
        self.target_vol = target_vol
        self.lookback = lookback

    def size(self, request: SizingInput) -> float:
        vol = _trailing_vol(request.df, self.lookback)

        if vol is None:
            return 0.0

        scale = self.target_vol / vol
        target_notional = request.equity * self.base_pct * scale

        if request.direction == 1:
            target_notional = min(target_notional, request.cash)

        return self.cost_model.max_shares(request.price, target_notional)
