"""Base classes for alpha models — robust, agent-safe templates.

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
base and MAY NOT be overridden by subclasses — ``__init_subclass__``
raises if it is.

Robustness layers applied uniformly across all three bases:

    1. Symbol passed to every ``compute_*`` hook so subclasses can
       implement ticker-conditional logic.
    2. ``required_columns: ClassVar[tuple[str, ...]]`` — base filters
       out frames missing declared OHLCV columns before calling
       ``compute_*``. Default is ``("close",)``.
    3. NaN / Inf guard on returned scores — non-finite is treated as
       ``None`` (skip) so malformed scores never leak into Insights.
    4. ``__init_subclass__`` checks at class-definition time — enforces
       ``name: str`` is set and ``update`` is not overridden.
    5. One-shot instance preflight on the first ``update()`` call —
       validates ``lookback``, ``hold_days`` (and ``pairs`` for
       ``PairAlpha``). Flag-gated so overhead is paid once per alpha.

If your alpha doesn't fit any of the three bases (event streams,
external data injected through a side channel), implement the
``AlphaModel`` protocol directly — inheritance is optional, the
protocol is the only real contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING, Any, ClassVar

import math

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


def _is_finite(value: float) -> bool:
    """True if ``value`` is a real finite number (not NaN, not Inf)."""
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _has_required_columns(df: "pd.DataFrame", required: tuple[str, ...]) -> bool:
    """True if ``df`` has every column name in ``required``."""
    columns = df.columns

    for col in required:
        if col not in columns:
            return False

    return True


#     ================================
# --> Shared subclass validator
#     ================================

def _validate_subclass_shape(cls: type, base_name: str) -> None:
    """Enforce ``name`` attr + no ``update`` override. Called from
    ``__init_subclass__`` on each base."""
    # Reason: skip validation for abstract intermediates — only concrete
    # leaves should have a non-empty ``name``.
    if getattr(cls, "__abstractmethods__", None):
        return

    name = getattr(cls, "name", None)

    if not isinstance(name, str) or not name:
        raise TypeError(
            f"{cls.__name__} must set class attribute `name: str` "
            f"(unique identifier used by multi-alpha PCMs to partition "
            f"insights by source).",
        )

    if "update" in cls.__dict__:
        raise TypeError(
            f"{cls.__name__} overrides `update` — the {base_name} base "
            f"owns pipeline semantics. Implement the `compute_*` hook "
            f"instead; `update` must not be overridden.",
        )


#     ================================
# --> Per-symbol base
#     ================================

class PerSymbolAlpha(ABC):
    """Base for alphas that score each ticker independently.

    Subclass contract:

        name:               ClassVar[str] — unique identifier.
        lookback:           int > 0 (instance attr) — bars required.
        hold_days:          int > 0 (instance attr) — Insight horizon.
        required_columns:   ClassVar[tuple[str, ...]] — OHLCV columns
                            this alpha needs. Default ``("close",)``.

        compute_score(symbol, df) -> float | None:
            Return a signed score. Positive = long, negative = short,
            zero = flat. Return ``None`` to skip this symbol (missing
            data, bad price, degenerate sample). Return value must be
            finite — NaN / Inf are treated as ``None`` by the base.

    Do NOT override ``update`` — enforced by ``__init_subclass__``.
    """

    name: str
    lookback: int
    hold_days: int

    required_columns: ClassVar[tuple[str, ...]] = ("close",)

    _preflight_done: bool = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _validate_subclass_shape(cls, "PerSymbolAlpha")

    def _preflight(self) -> None:
        """Validate instance attrs. Called once on first ``update()``."""
        if not isinstance(self.lookback, int) or self.lookback <= 0:
            raise ValueError(
                f"{type(self).__name__}.lookback must be a positive int, "
                f"got {self.lookback!r}",
            )

        if not isinstance(self.hold_days, int) or self.hold_days <= 0:
            raise ValueError(
                f"{type(self).__name__}.hold_days must be a positive int, "
                f"got {self.hold_days!r}",
            )

        if not self.required_columns:
            raise ValueError(
                f"{type(self).__name__}.required_columns cannot be empty",
            )

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        if not self._preflight_done:
            self._preflight()
            self._preflight_done = True

        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            if not _has_required_columns(df, self.required_columns):
                continue

            score = self.compute_score(symbol, df)

            if score is None or not _is_finite(score):
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
    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        """Signed score for one symbol, or None to skip.

        Args:
            symbol: Ticker being scored.
            df: OHLCV slice up to and including the current bar.
                Guaranteed to have ``len(df) >= self.lookback`` and
                every column in ``self.required_columns``.
        """


#     ================================
# --> Cross-sectional base
#     ================================

class CrossSectionalAlpha(ABC):
    """Base for alphas that score tickers against universe-wide stats.

    Two-phase ``update``:

        1. ``compute_universe_stats(ctx)`` runs once per bar across the
           full universe. Returns whatever shape the alpha needs.
        2. ``compute_score(symbol, df, stats)`` runs per ticker, using
           the precomputed stats.

    Subclass contract:

        name, lookback, hold_days, required_columns: as PerSymbolAlpha.

        compute_universe_stats(ctx) -> T:
            Return precomputed stats for this bar. Return ``None`` to
            signal "universe not ready this bar" — the base emits an
            empty list.

        compute_score(symbol, df, stats) -> float | None:
            Signed score using ``stats``. Receives the ticker symbol so
            subclasses look up per-symbol values without value-matching
            hacks.

    Do NOT override ``update`` — enforced by ``__init_subclass__``.
    """

    name: str
    lookback: int
    hold_days: int

    required_columns: ClassVar[tuple[str, ...]] = ("close",)

    _preflight_done: bool = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _validate_subclass_shape(cls, "CrossSectionalAlpha")

    def _preflight(self) -> None:
        if not isinstance(self.lookback, int) or self.lookback <= 0:
            raise ValueError(
                f"{type(self).__name__}.lookback must be a positive int, "
                f"got {self.lookback!r}",
            )

        if not isinstance(self.hold_days, int) or self.hold_days <= 0:
            raise ValueError(
                f"{type(self).__name__}.hold_days must be a positive int, "
                f"got {self.hold_days!r}",
            )

        if not self.required_columns:
            raise ValueError(
                f"{type(self).__name__}.required_columns cannot be empty",
            )

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        if not self._preflight_done:
            self._preflight()
            self._preflight_done = True

        stats = self.compute_universe_stats(ctx)

        if stats is None:
            return []

        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            if not _has_required_columns(df, self.required_columns):
                continue

            score = self.compute_score(symbol, df, stats)

            if score is None or not _is_finite(score):
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
        """Precompute universe-wide stats for this bar, or ``None`` to skip."""

    @abstractmethod
    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: Any,
    ) -> float | None:
        """Signed score for one symbol using precomputed universe stats."""


#     ================================
# --> Pair base
#     ================================

class PairAlpha(ABC):
    """Base for stat-arb alphas emitting paired long/short Insights.

    Each firing pair emits exactly two Insights — opposite directions,
    equal magnitude — so PCMs see a dollar-neutral signal.

    Subclass contract:

        name, lookback, hold_days, required_columns: as PerSymbolAlpha.
        pairs: list[tuple[str, str]] — ticker pairs this alpha watches.
               Populate in ``__init__``. Order matters: ``(A, B)`` =>
               "positive score longs A, shorts B."

        compute_pair_score(sym_a, sym_b, df_a, df_b) -> float | None:
            Signed score for the pair. Positive = long A / short B.
            Negative = short A / long B. ``None`` to skip the pair.
            Both dfs are guaranteed to have ``len >= self.lookback``
            and all columns in ``self.required_columns``.

    Do NOT override ``update`` — enforced by ``__init_subclass__``.
    """

    name: str
    lookback: int
    hold_days: int
    pairs: list[tuple[str, str]]

    required_columns: ClassVar[tuple[str, ...]] = ("close",)

    _preflight_done: bool = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _validate_subclass_shape(cls, "PairAlpha")

    def _preflight(self) -> None:
        if not isinstance(self.lookback, int) or self.lookback <= 0:
            raise ValueError(
                f"{type(self).__name__}.lookback must be a positive int, "
                f"got {self.lookback!r}",
            )

        if not isinstance(self.hold_days, int) or self.hold_days <= 0:
            raise ValueError(
                f"{type(self).__name__}.hold_days must be a positive int, "
                f"got {self.hold_days!r}",
            )

        if not self.required_columns:
            raise ValueError(
                f"{type(self).__name__}.required_columns cannot be empty",
            )

        if not self.pairs:
            raise ValueError(
                f"{type(self).__name__}.pairs cannot be empty",
            )

        seen: set[tuple[str, str]] = set()

        for sym_a, sym_b in self.pairs:
            if sym_a == sym_b:
                raise ValueError(
                    f"{type(self).__name__}: self-pair ({sym_a}, {sym_b}) "
                    f"not allowed",
                )

            key = tuple(sorted((sym_a, sym_b)))

            if key in seen:
                raise ValueError(
                    f"{type(self).__name__}: duplicate pair {sym_a}/{sym_b} "
                    f"(pairs must be unique regardless of leg order)",
                )

            seen.add(key)

    def update(self, ctx: "AlgorithmContext") -> list[Insight]:
        if not self._preflight_done:
            self._preflight()
            self._preflight_done = True

        close_time = ctx.timestamp + timedelta(days=self.hold_days)

        out: list[Insight] = []

        for sym_a, sym_b in self.pairs:
            df_a = ctx.data.get(sym_a)
            df_b = ctx.data.get(sym_b)

            if df_a is None or df_b is None:
                continue

            if len(df_a) < self.lookback or len(df_b) < self.lookback:
                continue

            if not _has_required_columns(df_a, self.required_columns):
                continue

            if not _has_required_columns(df_b, self.required_columns):
                continue

            score = self.compute_pair_score(sym_a, sym_b, df_a, df_b)

            if score is None or not _is_finite(score):
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
        self,
        sym_a: str,
        sym_b: str,
        df_a: "pd.DataFrame",
        df_b: "pd.DataFrame",
    ) -> float | None:
        """Signed score for one ticker pair, or None to skip.

        Positive score => long leg A, short leg B. Negative => flip.
        Both dfs are sliced to the current bar and have
        ``len >= self.lookback`` plus all ``required_columns``.
        """
