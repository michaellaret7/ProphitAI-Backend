"""Shared helpers for PortfolioConstructionModels.

Extracted so every PCM uses the same:
  - cross-sectional z-scoring (with winsorization)
  - rebalance-cadence gate
  - weight → shares conversion
  - "close-orphan-positions" logic (positions held but not in the new book)

None of these are public API — PCMs import them internally.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from math import sqrt
from typing import TYPE_CHECKING

from prophitai_algo_trading.core.models import Insight, PortfolioTarget

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext


#     ================================
# --> Dedupe insights by symbol
#     ================================

def dedupe_insights(insights: list[Insight]) -> list[Insight]:
    """Collapse multiple insights per symbol to one.

    When multiple alphas emit for the same symbol, keep the insight with
    the highest ``|direction * magnitude|`` — i.e., the most confident
    directional call. This is the consistent policy across all PCMs that
    expect one-insight-per-symbol input.

    Preserves original order for unique symbols.
    """
    best: dict[str, Insight] = {}

    for insight in insights:
        score = abs(insight.direction * (insight.magnitude or 0.0))

        existing = best.get(insight.symbol)

        if existing is None:
            best[insight.symbol] = insight
            continue

        existing_score = abs(existing.direction * (existing.magnitude or 0.0))

        if score > existing_score:
            best[insight.symbol] = insight

    return list(best.values())


#     ================================
# --> Cross-sectional z-score
#     ================================

def cross_sectional_zscore(
    values: dict[str, float],
    winsor_at: float | None = 3.0,
) -> dict[str, float]:
    """Return {symbol: z-scored value}. Missing or None → 0.0.

    Sample std-dev (n-1 denominator). Fewer than 3 valid values or zero
    variance → all z-scores collapse to 0 (no cross-sectional signal).
    """
    clean = {s: v for s, v in values.items() if v is not None}

    if len(clean) < 3:
        return {s: 0.0 for s in values}

    vs = list(clean.values())

    mean_v = sum(vs) / len(vs)
    var_v = sum((v - mean_v) ** 2 for v in vs) / (len(vs) - 1)
    std_v = sqrt(var_v) if var_v > 0.0 else 0.0

    if std_v <= 0.0:
        return {s: 0.0 for s in values}

    out: dict[str, float] = {}

    for sym, v in values.items():
        if v is None:
            out[sym] = 0.0
            continue

        z = (v - mean_v) / std_v

        if winsor_at is not None:
            z = max(-winsor_at, min(winsor_at, z))

        out[sym] = z

    return out


#     ================================
# --> Rebalance scheduler
#     ================================

class RebalanceScheduler:
    """Gates PCMs to only emit targets on rebalance bars.

    ``rebalance_every = None`` means "every bar is a rebalance bar".
    A ``timedelta`` means "at least this long has passed since the
    last rebalance." Compared against ``ctx.timestamp`` directly — no
    calendar-aware logic, so bar-count semantics work as long as the
    data frequency is consistent.
    """

    def __init__(self, rebalance_every: timedelta | None = None):
        self._every = rebalance_every
        self._last: datetime | None = None

    def is_rebalance_bar(self, timestamp: datetime) -> bool:
        if self._every is None:
            return True

        if self._last is None:
            self._last = timestamp
            return True

        if (timestamp - self._last) >= self._every:
            self._last = timestamp
            return True

        return False


#     ================================
# --> Weight → shares
#     ================================

def weight_to_shares(
    ctx: "AlgorithmContext",
    symbol: str,
    weight: float,
    direction: int,
) -> float | None:
    """Convert a signed-intent weight to target shares at the current price.

    Returns ``None`` if the symbol has no price available (shouldn't
    happen if the alpha emitted an insight, but defensive).
    """
    df = ctx.data.get(symbol)

    if df is None or df.empty:
        return None

    price = float(df["close"].iloc[-1])

    if price <= 0.0:
        return None

    equity = ctx.portfolio.equity()

    notional = equity * weight

    return (notional * direction) / price


#     ================================
# --> Close orphans
#     ================================

def append_close_orphans(
    ctx: "AlgorithmContext",
    targets: list[PortfolioTarget],
) -> list[PortfolioTarget]:
    """For every currently-invested symbol not already in ``targets``,
    append a zero-share target so Execution closes it.

    Idempotent: if a symbol is already present with target_shares=0, no
    duplicate is added.
    """
    chosen = {t.symbol for t in targets}

    out = list(targets)

    for symbol in ctx.portfolio.positions:
        if symbol in chosen:
            continue

        out.append(PortfolioTarget(symbol=symbol, target_shares=0.0))

    return out
