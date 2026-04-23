"""Pipeline stage protocols for the algorithm framework.

Each stage is a ``Protocol`` — duck typing, no inheritance required. A
concrete model passes the structural type check by providing the
documented attributes and methods.

Pipeline order (see framework.md for full ADR):

    AlphaModel.update(ctx) ─▶ list[Insight]
                               │
    PortfolioConstructionModel.create_targets(ctx, insights) ─▶ list[PortfolioTarget]
                               │
    RiskManagementModel.manage(ctx, targets) ─▶ list[PortfolioTarget]
                               │
    ExecutionModel.execute(ctx, targets) ─▶ (side effects only)

Non-goal: enforce these as ABCs. ``Protocol`` keeps implementations free of
inheritance chains and makes composition the default (`CompositeRiskModel`
holds a list of other ``RiskManagementModel`` instances, no class hierarchy).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)


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
class PortfolioConstructionModel(Protocol):
    """Blends Insights into concrete PortfolioTargets.

    Owns rebalance cadence, weight scheme, and position cap logic. All
    weight-to-shares math runs through
    ``framework.portfolio_construction.base.weight_to_shares`` so every
    PCM uses identical conversion semantics.

    Returns a full list of targets for the book *this bar*. Symbols not in
    the returned list are treated as "no target" — existing positions in
    those symbols stay as-is (Execution doesn't close them unilaterally
    based on omission). If you want to close a position, emit a target
    with ``target_shares=0.0``.
    """

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
    """Turns PortfolioTargets into actual orders (sim or broker).

    Pure side-effect stage. Returns nothing — mutation lives on
    ``ctx.portfolio`` (simulated) or goes out to the broker (live).

    Implementations:
        - ``SimulatedExecutionModel``: diffs current portfolio vs. targets,
          calls ``portfolio.open`` / ``portfolio.close`` with a fill price
          (typically the current bar's close or the next bar's open).
        - ``BrokerExecutionModel``: same diff, but calls
          ``broker.buy`` / ``broker.sell`` / ``broker.close_position``.

    Should no-op when ``ctx.warmup`` is True.
    """

    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None: ...
