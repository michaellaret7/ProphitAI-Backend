"""Base classes for alpha models.

Three templates cover ~100% of alpha patterns. Pick the one that matches
the semantics of your signal; each base owns ``Insight`` construction
so subclasses only implement the scoring math.

    PerSymbolAlpha
        Score each ticker independently from its own history.
        momentum, breakout, reversal, volatility, RSI, MACD, fundamentals.

    CrossSectionalAlpha
        Score each ticker against universe-wide statistics.
        low-vol anomaly, rank-based L/S, size, value vs. peers, dispersion.

    PairAlpha
        Score ticker *pairs* for stat-arb. Emits paired long/short
        ``Insight``s for each firing pair — one leg per ticker.
        cointegration, relative value, sector-neutral pairs.

All three satisfy the ``AlphaModel`` protocol (``name``, ``lookback``,
``update(ctx) -> list[Insight]``). ``update`` is implemented on each
base; subclasses must not override it. Only the ``compute_*`` hooks are
subclass responsibility.

If your alpha doesn't fit any of these three (e.g. emits Insights from
event streams, uses external data injected through a side channel),
implement the ``AlphaModel`` protocol directly — inheritance is
optional, the protocol is the only real contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from prophitai_algo_trading.core.models import Insight

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext


#     ================================
# --> Helper funcs
#     ================================

def _direction_from_score(score: float) -> int:
    """Sign of ``score`` mapped to Insight.direction domain (+1 / -1 / 0)."""
    if score > 0.0:
        return 1

    if score < 0.0:
        return -1

    return 0


#     ================================
# --> Per-symbol base
#     ================================

class PerSymbolAlpha(ABC):
    """Base for alphas that score each ticker independently.

    Use this when the signal is computable from one ticker's own history
    — the vast majority of technical/fundamental alphas.

    Subclass contract:

        name:       ClassVar[str] — unique identifier used by multi-alpha
                    PCMs to partition insights by source. Set at class level.
        lookback:   int (instance or class attr) — bars of history a symbol
                    needs before the alpha emits for it.
        hold_days:  int (instance or class attr) — Insight ``close_time``
                    horizon in calendar days.

        compute_score(df) -> float | None:
            Return a signed score. Positive = long, negative = short,
            zero = flat. Return ``None`` to skip this symbol (missing
            data, bad price, degenerate sample). The base class handles
            direction derivation + ``abs(score)`` for magnitude.

    Do NOT override ``update`` — the base class owns Insight construction
    so the per-alpha contract stays consistent across the framework.
    """

    name: str
    lookback: int
    hold_days: int

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            score = self.compute_score(df)

            if score is None:
                continue

            out.append(Insight(
                symbol=symbol,
                direction=_direction_from_score(score),
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(score),
                source_alpha=self.name,
            ))

        return out

    @abstractmethod
    def compute_score(self, df: "pd.DataFrame") -> float | None:
        """Signed score for one symbol, or None to skip.

        Args:
            df: OHLCV slice up to and including the current bar. Guaranteed
                to have ``len(df) >= self.lookback``.

        Returns:
            Signed score (positive = long, negative = short), or ``None``
            to skip emission for this symbol (e.g. degenerate sample).
        """


#     ================================
# --> Cross-sectional base
#     ================================

class CrossSectionalAlpha(ABC):
    """Base for alphas that score tickers against universe-wide stats.

    Use this when the signal depends on how one ticker compares to the
    rest of the universe — low-vol anomaly, rank-based L/S, dispersion.

    Two-phase ``update``:

        1. ``compute_universe_stats(ctx)`` runs once per bar across the
           full universe. Returns whatever shape the alpha needs
           (median, rank array, percentile table, regime flag, etc.).
        2. ``compute_score(df, stats)`` runs per ticker, using the
           precomputed stats.

    Subclass contract:

        name, lookback, hold_days: as PerSymbolAlpha.

        compute_universe_stats(ctx) -> T:
            Return precomputed stats for this bar. Return ``None`` to
            signal "universe not ready this bar" — the base will emit
            an empty list.

        compute_score(df, stats) -> float | None:
            Signed score using ``stats``. Same semantics as
            PerSymbolAlpha.compute_score.

    Do NOT override ``update``.
    """

    name: str
    lookback: int
    hold_days: int

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        stats = self.compute_universe_stats(ctx)

        if stats is None:
            return []

        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            score = self.compute_score(df, stats)

            if score is None:
                continue

            out.append(Insight(
                symbol=symbol,
                direction=_direction_from_score(score),
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(score),
                source_alpha=self.name,
            ))

        return out

    @abstractmethod
    def compute_universe_stats(self, ctx: "AlgorithmContext") -> Any:
        """Precompute universe-wide stats for this bar.

        Return whatever shape the alpha needs to score one ticker against
        the universe (e.g. ``{"median_sigma": 0.021}`` for low-vol, a
        ``pd.Series`` of ranks for rank-based alphas). Return ``None`` if
        the universe isn't ready (e.g. too few symbols have data yet).
        """

    @abstractmethod
    def compute_score(
        self, df: "pd.DataFrame", stats: Any,
    ) -> float | None:
        """Signed score for one symbol using precomputed universe stats."""


#     ================================
# --> Pair base
#     ================================

class PairAlpha(ABC):
    """Base for stat-arb alphas emitting paired long/short Insights.

    Use this for cointegration, relative-value, or sector-neutral pair
    strategies where the signal is about a *pair*, not an individual
    ticker. Each firing pair emits exactly two Insights with opposite
    directions and equal magnitude — PCMs see a dollar-neutral signal.

    Subclass contract:

        name, lookback, hold_days: as PerSymbolAlpha.

        pairs: list[tuple[str, str]] — ticker pairs this alpha watches.
            Populate in ``__init__``. Order matters: ``(A, B)`` means
            "positive score longs A, shorts B."

        compute_pair_score(df_a, df_b) -> float | None:
            Signed score for the pair. Positive = long leg A / short
            leg B. Negative = short A / long B. ``None`` to skip the
            pair (missing data, degenerate cointegration, etc.). Both
            dfs are guaranteed to have ``len >= self.lookback``.

    Do NOT override ``update``. Both legs of a firing pair always emit
    together so the PCM sees a self-consistent signal.
    """

    name: str
    lookback: int
    hold_days: int
    pairs: list[tuple[str, str]]

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for sym_a, sym_b in self.pairs:
            df_a = ctx.data.get(sym_a)
            df_b = ctx.data.get(sym_b)

            if df_a is None or df_b is None:
                continue

            if len(df_a) < self.lookback or len(df_b) < self.lookback:
                continue

            score = self.compute_pair_score(df_a, df_b)

            if score is None:
                continue

            # Reason: positive score => long A / short B; flip on negative.
            direction_a = 1 if score > 0.0 else -1 if score < 0.0 else 0
            direction_b = -direction_a

            magnitude = abs(score)

            out.append(Insight(
                symbol=sym_a,
                direction=direction_a,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=magnitude,
                source_alpha=self.name,
            ))

            out.append(Insight(
                symbol=sym_b,
                direction=direction_b,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=magnitude,
                source_alpha=self.name,
            ))

        return out

    @abstractmethod
    def compute_pair_score(
        self, df_a: "pd.DataFrame", df_b: "pd.DataFrame",
    ) -> float | None:
        """Signed score for one ticker pair, or None to skip.

        Positive score => long leg A, short leg B. Negative => flip.
        Both dfs are sliced to the current bar and have ``len >= lookback``.
        """
