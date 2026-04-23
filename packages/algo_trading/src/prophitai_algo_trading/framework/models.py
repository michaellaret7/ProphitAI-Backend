"""Core dataclasses for the algorithm framework.

Three types define the contracts between pipeline stages:

    AlphaModel  ─▶  list[Insight]  ─▶  PortfolioConstructionModel
                                       │
                                       ▼
                                  list[PortfolioTarget]
                                       │
                                       ▼
                                  RiskManagementModel
                                       │
                                       ▼
                                  list[PortfolioTarget]  (possibly modified)
                                       │
                                       ▼
                                  ExecutionModel

``AlgorithmContext`` is a read-snapshot of algorithm state, passed to every
stage on every bar. Its ``portfolio`` attribute *is* mutable — the execution
stage intentionally mutates it — but all other attributes are frozen for
the duration of a single bar's pipeline run.

These types are deliberately thin. Anything domain-specific (ranking,
weighting, sizing, cooldown state) belongs inside a model implementation,
not on these dataclasses. Keep the contracts small.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.portfolio import Portfolio


#     ================================
# --> Alpha → PCM contract
#     ================================

@dataclass(frozen=True)
class Insight:
    """A typed prediction from an AlphaModel.

    An Insight is not a signal in the "position column" sense — it's a
    structured claim about where a symbol is going, with optional magnitude
    and confidence. The PortfolioConstructionModel blends Insights (possibly
    from multiple alphas) into target weights.

    Attributes:
        symbol: Ticker the prediction is about.
        direction: -1 (down / short), 0 (flat / exit), +1 (up / long).
            Uses int to match the existing ``position`` convention; the
            package-level ``Direction`` enum is LONG/SHORT only and has no
            flat state, so it's the wrong type here.
        generated_time: Bar timestamp the alpha produced this insight on.
        close_time: When the prediction expires — the PCM may keep a
            target alive until ``close_time`` passes, even if the alpha
            stops emitting for this symbol.
        magnitude: Optional expected return (as a decimal, e.g. 0.02 = +2%).
            Not standardized — alphas may use return, z-score, Donchian
            position, etc. The PCM z-scores cross-sectionally before
            combining.
        confidence: Optional 0..1 confidence score. PCM may weight by this.
        weight: Optional relative weight hint vs. other insights from the
            same alpha. None = equal among its alpha's cohort.
        source_alpha: Name of the AlphaModel that produced this insight.
            Used by multi-alpha PCMs to blend per-alpha z-scores before
            combining — not for logging alone.
    """

    symbol: str
    direction: int
    generated_time: datetime
    close_time: datetime
    magnitude: float | None = None
    confidence: float | None = None
    weight: float | None = None
    source_alpha: str = ""


#     ================================
# --> PCM → Risk → Execution contract
#     ================================

@dataclass(frozen=True)
class PortfolioTarget:
    """Target book state for a single symbol.

    ``target_shares`` is signed: positive for long, negative for short, zero
    to close any existing position. ExecutionModel diffs against current
    holdings to decide what to trade.

    Shares are ``float`` — Alpaca supports fractional shares natively. An
    execution model that needs integer sizes should round at its own
    boundary, not here.

    PCMs that think in percentages should convert via:
        target_shares = equity * pct / price
    at target-creation time, so the PCM's output is always concrete.
    """

    symbol: str
    target_shares: float


#     ================================
# --> Per-bar algorithm state
#     ================================

@dataclass
class AlgorithmContext:
    """Read-mostly snapshot of algorithm state for one bar.

    Passed as the first argument to every model call. Models should treat
    this as read-only *except* for the ``portfolio`` attribute, which the
    ExecutionModel deliberately mutates by placing orders.

    Attributes:
        timestamp: The current bar's timestamp. Fixed for the duration of
            one pipeline pass.
        portfolio: Mutable portfolio state. Alphas / PCMs / Risk read from
            it; Execution writes to it. Frozen between bars.
        data: Per-ticker OHLCV history up to and including ``timestamp``.
            Keyed by ticker. Engines build this by slicing each ticker's
            full DataFrame at every bar.
        warmup: True while the engine is in warmup mode (indicators update
            but orders are suppressed). Models should honor this flag and
            skip ``execute()`` work when warm.
    """

    timestamp: datetime
    portfolio: "Portfolio"
    data: dict[str, "pd.DataFrame"]
    warmup: bool = False
