"""Risk-based sizer: ATRRisk (shares sized by stop distance)."""

from __future__ import annotations

import math

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.sizing.base import BaseSizer, SizingInput


def _latest_atr(df: pd.DataFrame, atr_column: str | None) -> float | None:
    """Return the latest ATR value, scanning common column names if none given."""
    if df.empty:
        return None

    candidates = (
        [atr_column] if atr_column else
        [c for c in df.columns if c.startswith("atr_") or c == "atr"]
    )

    for col in candidates:
        if col is None or col not in df.columns:
            continue

        value = df[col].iloc[-1]

        if pd.notna(value) and value > 0:
            return float(value)

    return None


class ATRRiskSizer(BaseSizer):
    """Risk a fixed fraction of equity per trade using ATR as the stop distance.

    Shares = (equity * risk_pct) / (atr * atr_multiplier).

    Args:
        risk_pct: Fraction of equity risked per trade (0.01 = 1%).
        atr_multiplier: Stop distance in ATR units.
        atr_column: Name of the ATR column on the strategy frame. If None,
            auto-detects a column starting with ``atr_`` or named ``atr``.
        cost_model: Transaction costs.
    """

    def __init__(
        self,
        risk_pct: float = 0.01,
        atr_multiplier: float = 2.0,
        atr_column: str | None = None,
        cost_model: CostModel | None = None,
    ):
        super().__init__(cost_model)
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier
        self.atr_column = atr_column

    def size(self, request: SizingInput) -> float:
        atr_value = _latest_atr(request.df, self.atr_column)

        if atr_value is None:
            return 0.0

        stop_distance = atr_value * self.atr_multiplier

        if stop_distance <= 0:
            return 0.0

        risk_budget = request.equity * self.risk_pct
        raw_shares = risk_budget / stop_distance

        notional = raw_shares * request.price

        if request.direction == 1:
            max_affordable = self.cost_model.max_shares(request.price, request.cash)
            raw_shares = min(raw_shares, max_affordable)
        elif notional > request.equity:
            raw_shares = self.cost_model.max_shares(request.price, request.equity)

        return math.floor(raw_shares) if raw_shares >= 1 else 0.0
