from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

class PivotPoints:
    def __init__(self, ohlcv: pd.DataFrame):
        self.df = ohlcv.copy()
        # Expect columns: open, high, low, close, volume
        if not set(["open", "high", "low", "close"]).issubset(self.df.columns):
            raise ValueError("OHLC dataframe must contain open, high, low, close columns")

    @property
    def _prev(self) -> dict[str, pd.Series]:
        """Previous period OHLC used for pivot calculations."""
        return {
            "open": self.df["open"].shift(1),
            "high": self.df["high"].shift(1),
            "low": self.df["low"].shift(1),
            "close": self.df["close"].shift(1),
        }

    # -----------------------------
    # Classic (Standard) Pivots
    # -----------------------------
    def classic(self) -> pd.DataFrame:
        """Classic pivot points using previous period H/L/C.

        P = (H + L + C) / 3
        R1 = 2P - L, S1 = 2P - H
        R2 = P + (H - L), S2 = P - (H - L)
        R3 = P + 2(H - L), S3 = P - 2(H - L)
        """
        ph = self._prev["high"]
        pl = self._prev["low"]
        pc = self._prev["close"]
        rng = ph - pl
        pivot = (ph + pl + pc) / 3.0
        r1 = 2 * pivot - pl
        s1 = 2 * pivot - ph
        r2 = pivot + rng
        s2 = pivot - rng
        r3 = pivot + 2 * rng
        s3 = pivot - 2 * rng

        out = pd.DataFrame({
            "s3": s3, "s2": s2, "s1": s1,
            "pivot": pivot,
            "r1": r1, "r2": r2, "r3": r3,
        })
        return out

    # -----------------------------
    # Fibonacci Pivots
    # -----------------------------
    def fibonacci(self) -> pd.DataFrame:
        """Fibonacci pivot points using previous period H/L/C.

        P = (H + L + C)/3, range = H - L
        Levels at 0.382, 0.618, 1.000 of range added/subtracted from P.
        """
        ph = self._prev["high"]
        pl = self._prev["low"]
        pc = self._prev["close"]
        rng = ph - pl
        pivot = (ph + pl + pc) / 3.0

        r1 = pivot + 0.382 * rng
        s1 = pivot - 0.382 * rng
        r2 = pivot + 0.618 * rng
        s2 = pivot - 0.618 * rng
        r3 = pivot + 1.000 * rng
        s3 = pivot - 1.000 * rng

        out = pd.DataFrame({
            "s3": s3, "s2": s2, "s1": s1,
            "pivot": pivot,
            "r1": r1, "r2": r2, "r3": r3,
        })
        return out

    # -----------------------------
    # Camarilla Pivots
    # -----------------------------
    def camarilla(self) -> pd.DataFrame:
        """Camarilla pivot points using previous period values.

        Uses close plus 1.1 * range multipliers for R/S levels.
        We report pivot as (H + L + C)/3 to align with common tables.
        Multipliers: 1.1/12, 1.1/6, 1.1/4 for R1..R3 and S1..S3.
        """
        ph = self._prev["high"]
        pl = self._prev["low"]
        pc = self._prev["close"]
        rng = ph - pl
        pivot = (ph + pl + pc) / 3.0
        k1, k2, k3 = 1.1 / 12.0, 1.1 / 6.0, 1.1 / 4.0

        r1 = pc + k1 * rng
        r2 = pc + k2 * rng
        r3 = pc + k3 * rng
        s1 = pc - k1 * rng
        s2 = pc - k2 * rng
        s3 = pc - k3 * rng

        out = pd.DataFrame({
            "s3": s3, "s2": s2, "s1": s1,
            "pivot": pivot,
            "r1": r1, "r2": r2, "r3": r3,
        })
        return out

    # -----------------------------
    # Woodie's Pivots
    # -----------------------------
    def woodie(self) -> pd.DataFrame:
        """Woodie's pivot points using previous period values.

        P = (H + L + 2C) / 4 ; rest as Classic with this P.
        """
        ph = self._prev["high"]
        pl = self._prev["low"]
        pc = self._prev["close"]
        rng = ph - pl
        pivot = (ph + pl + 2.0 * pc) / 4.0
        r1 = 2 * pivot - pl
        s1 = 2 * pivot - ph
        r2 = pivot + rng
        s2 = pivot - rng
        r3 = pivot + 2 * rng
        s3 = pivot - 2 * rng

        out = pd.DataFrame({
            "s3": s3, "s2": s2, "s1": s1,
            "pivot": pivot,
            "r1": r1, "r2": r2, "r3": r3,
        })
        return out

    # -----------------------------
    # DeMark's Pivots
    # -----------------------------
    def demark(self) -> pd.DataFrame:
        """DeMark's pivot using conditional X from previous period O/H/L/C.

        if C < O: X = H + 2L + C
        elif C > O: X = 2H + L + C
        else: X = H + L + 2C
        P = X / 4 ; R1 = X/2 - L ; S1 = X/2 - H
        """
        po = self._prev["open"]
        ph = self._prev["high"]
        pl = self._prev["low"]
        pc = self._prev["close"]

        x = pd.Series(np.nan, index=self.df.index)
        x = x.mask(pc < po, ph + 2.0 * pl + pc)
        x = x.mask(pc > po, 2.0 * ph + pl + pc)
        x = x.fillna(ph + pl + 2.0 * pc)

        pivot = x / 4.0
        r1 = x / 2.0 - pl
        s1 = x / 2.0 - ph

        out = pd.DataFrame({
            "s3": np.nan, "s2": np.nan, "s1": s1,
            "pivot": pivot,
            "r1": r1, "r2": np.nan, "r3": np.nan,
        })
        return out