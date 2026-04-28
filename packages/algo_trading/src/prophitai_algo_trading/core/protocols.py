"""Pipeline stage protocols for the algorithm framework.

Each stage is a ``Protocol`` — duck typing, no inheritance required. A
concrete model passes the structural type check by providing the
documented attributes and methods.

Pipeline order (see framework.md for full ADR):

    AlphaModel.update(ctx) ─▶ list[Insight]
                               │
    PortfolioConstructor.create_targets(ctx, insights) ─▶ list[PortfolioTarget]
                               │
    RiskManagementModel.manage(ctx, targets) ─▶ list[PortfolioTarget]
                               │
    ExecutionModel.execute(ctx, targets) ─▶ (side effects only)

Non-goal: enforce these as ABCs. ``Protocol`` keeps implementations free of
inheritance chains and makes composition the default (`CompositeRiskModel`
holds a list of other ``RiskManagementModel`` instances, no class hierarchy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Stage 1 — Alpha
#     ================================

@runtime_checkable
class AlphaModel(Protocol):
    """Produces Insights from per-bar data.

    Concrete alphas should be small, single-purpose, and stateless-ish —
    any rolling state (EMAs, deques) is fine, but avoid embedding
    sizing/risk/execution concerns. Keep the alpha focused on "what do I
    think this symbol is going to do."

    Attributes:
        name: Unique identifier used by multi-alpha PCMs to partition
            insights by source. Should match a key in a PCM's alpha-weight
            dict.
        lookback: Bars of history required before ``update`` produces
            useful insights. Engines skip alpha calls until this is met.

    Methods:
        update(ctx): Return a list of ``Insight`` for the current bar. May
            return an empty list on bars where nothing fires.
    """

    name: str
    lookback: int

    def update(self, ctx: AlgorithmContext) -> list[Insight]: ...


#     ================================
# --> Stage 2 — Portfolio Construction
#     ================================

@runtime_checkable
class PortfolioConstructor(Protocol):
    """Turns Insights into concrete PortfolioTargets.

    Owns selection (which names enter the book), sizing (how much per
    name), neutrality (dollar / sector / etc.), per-position caps, and
    rebalance cadence. All weight-to-shares math runs through
    ``construction.helpers.event.weight_to_shares`` so every constructor
    uses identical conversion semantics.

    Returns a full list of targets for the book *this bar*. Symbols not in
    the returned list are treated as "no target" — existing positions in
    those symbols stay as-is (Execution doesn't close them unilaterally
    based on omission). If you want to close a position, emit a target
    with ``target_shares=0.0``.

    Distinct from ``SignalBlender``: a constructor consumes one set of
    insights and produces actual positions; a blender consumes N sets of
    insights and produces a single composite, then delegates to a
    constructor.
    """

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]: ...


@runtime_checkable
class SignalBlender(Protocol):
    """Combines insights from multiple alphas into a single composite.

    Blends N per-alpha insight streams into one synthetic insight
    stream, then delegates to an inner ``PortfolioConstructor`` for the
    actual sizing. The ``inner`` field is the constructor it delegates
    to; without it a blender has nothing to deploy.

    Structurally a blender is also a ``PortfolioConstructor`` (it
    satisfies ``create_targets``) — but the role split makes it explicit
    that blending and constructing are different responsibilities.
    """

    inner: "PortfolioConstructor"

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]: ...


#     ================================
# --> Stage 3 — Risk Management
#     ================================

@runtime_checkable
class RiskManagementModel(Protocol):
    """Modifies PortfolioTargets based on portfolio-level risk state.

    Operates on the full target list *after* PCM and *before* Execution.
    Typical use: scale targets by a delever factor during drawdown, zero
    targets that breach sector caps, enforce max gross exposure.

    Every concrete ``RiskRule`` (stops, trails, limits, cooldowns,
    windows) is itself a complete ``RiskManagementModel`` — its own
    ``manage()`` wires the per-bar hooks (``on_bar`` / ``force_exit`` /
    ``block_entry``) onto the target list and overrides any target that
    would violate a stop with ``target_shares=0.0``.

    Multiple RiskManagementModels compose via ``CompositeRiskModel``, which
    runs them in sequence (each sees the output of the previous). Order
    matters — put portfolio-wide circuit breakers before position-level
    stops.
    """

    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]: ...


#     ================================
# --> Stage 4 — Execution
#     ================================

@runtime_checkable
class ExecutionModel(Protocol):
    """Turns PortfolioTargets into actual orders via an injected ``OrderSink``.

    Pure side-effect stage. Returns nothing — mutation lives on
    ``ctx.portfolio`` (via ``PortfolioSink``) or goes out to the broker
    plus a mirror update (via ``BrokerSink``). The decision matrix
    (flat/open/close/resize/flip + material-change tolerance) lives
    inside ``ExecutionModel``; the sink is responsible only for firing
    the resulting side-effect.

    Should no-op when ``ctx.warmup`` is True.
    """

    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None: ...


#     ================================
# --> Optional lifecycle contract
#     ================================

#     ================================
# --> Vectorized contracts
#     ================================

@runtime_checkable
class VectorAlpha(Protocol):
    """Vectorized alpha — produces a score panel from a price panel.

    Mirrors ``AlphaModel`` but operates on full-history panels rather
    than per-bar context. A single alpha class may satisfy *both*
    protocols (one ``update`` method for event-driven, one
    ``compute_panel`` method for vectorized) — duck typing only, no
    inheritance required.

    Attributes:
        name: Unique identifier — used by multi-alpha PCMs to partition
            score panels by source. Must match the ``AlphaModel.name``
            on the same class when both protocols are implemented.

    Methods:
        compute_panel(panel): Return a ``[date x ticker]`` DataFrame of
            signed scores. Positive = long candidate, negative = short
            candidate, NaN/0 = no signal. Index and columns must match
            ``panel.close`` exactly.
    """

    name: str

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame": ...


@runtime_checkable
class VectorPortfolioConstructor(Protocol):
    """Vectorized portfolio constructor.

    Consumes ``{alpha_name: score_panel}`` and returns a single
    ``[date x ticker]`` weight panel. Rows represent target weights at
    each bar (positive = long, negative = short, NaN/0 = flat).

    The constructor owns:
      - selection (which names enter the book),
      - sizing (magnitude / equal / quantile-cut),
      - neutrality (dollar / sector / etc.),
      - per-position caps,
      - rebalance cadence (returns a *dense* panel — non-rebalance
        rows must be forward-filled from the prior rebalance).

    Single-alpha constructors typically receive a 1-entry ``scores``
    dict; multi-alpha use cases run through a ``VectorSignalBlender``
    first, which collapses to a 1-entry dict before calling the
    constructor.

    Methods:
        build_weights(scores): Return a dense weight DataFrame.
            ``scores`` is keyed by alpha name; every value is a
            ``[date x ticker]`` panel with shared index and columns.
    """

    def build_weights(
        self, scores: dict[str, "pd.DataFrame"],
    ) -> "pd.DataFrame": ...


@runtime_checkable
class VectorSignalBlender(Protocol):
    """Vectorized signal blender.

    Combines multiple per-alpha score panels into a single composite
    score panel, then delegates to an inner ``VectorPortfolioConstructor``
    for the actual weight construction. Returns a weight panel by
    composition: blend → composite → inner.build_weights → weights.

    The blender owns blending policy (z-score, weighted sum, winsor);
    the inner owns selection / sizing / cadence.
    """

    inner: "VectorPortfolioConstructor"

    def build_weights(
        self, scores: dict[str, "pd.DataFrame"],
    ) -> "pd.DataFrame": ...


#     ================================
# --> Optional lifecycle contract (event-driven)
#     ================================

@runtime_checkable
class LifecycleAwareRiskModel(Protocol):
    """Optional lifecycle hook contract for ``RiskManagementModel``s.

    When a ``RiskManagementModel`` *also* structurally satisfies this
    protocol, the engine calls ``on_position_opened`` / ``on_position_closed``
    for every entry, exit, and flip that ``ExecutionModel`` produces.
    Risk rules that carry lifecycle state — trailing stops, time stops,
    consecutive-loss cooldowns — implement it. Rules that don't (static
    gross caps, drawdown delevers) skip it and never see the hooks.

    The engine gates calls with ``isinstance(risk, LifecycleAwareRiskModel)``
    once per step; risk models opt in structurally (no inheritance
    required).

    Methods:
        on_position_opened(ctx, symbol):
            Fired after a position opens (flat → long, flat → short, or
            the *open* leg of a flip).
        on_position_closed(ctx, symbol, pnl):
            Fired after a position closes (long → flat, short → flat, or
            the *close* leg of a flip). ``pnl`` is the realized P&L of
            the closing trade.
    """

    def on_position_opened(
        self,
        ctx: AlgorithmContext,
        symbol: str,
    ) -> None: ...

    def on_position_closed(
        self,
        ctx: AlgorithmContext,
        symbol: str,
        pnl: float,
    ) -> None: ...
