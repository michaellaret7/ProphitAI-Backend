"""Top-level Algorithm dataclass — the composed pipeline.

An ``Algorithm`` is the complete specification of a trading strategy at
the framework level: which alphas produce insights, how a PCM turns them
into targets, what risk management applies, and how execution reaches the
market.

Engines consume an ``Algorithm`` and drive its pipeline per bar. The same
``Algorithm`` instance runs in backtest and live — only the engine
(Backtest vs. LiveRunner) and the ``ExecutionModel``'s sink embedded
in the Algorithm differ (``PortfolioSink`` for backtest, ``BrokerSink``
for live).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prophitai_algo_trading.core.protocols import (
    AlphaModel,
    ExecutionModel,
    PortfolioConstructor,
    RiskManagementModel,
)


#     ================================
# --> Helper funcs
#     ================================

def _require_unique_alpha_names(alphas: list[AlphaModel]) -> None:
    """Raise if two alphas share a ``name`` — multi-alpha blenders key on it."""
    seen: set[str] = set()
    duplicates: list[str] = []

    for alpha in alphas:
        if alpha.name in seen:
            duplicates.append(alpha.name)
            continue

        seen.add(alpha.name)

    if duplicates:
        raise ValueError(
            f"Duplicate AlphaModel names: {sorted(set(duplicates))}. "
            "Each alpha must have a unique ``name`` — multi-alpha "
            "blenders partition insights by alpha name."
        )


#     ================================
# --> Algorithm
#     ================================

@dataclass
class Algorithm:
    """Composed trading-pipeline specification.

    Attributes:
        alphas: One or more AlphaModels. Insights from all alphas are
            concatenated before being passed to the PCM. Each alpha must
            have a unique ``name``.
        portfolio_construction: Single PortfolioConstructor that owns
            weighting + rebalance cadence. Multi-alpha blending happens
            outside the constructor via a ``SignalBlender`` wrapper
            (e.g. ``MultiAlphaBlender``) which delegates to a constructor.
        risk_management: Single RiskManagementModel. Use
            ``CompositeRiskModel`` to stack multiple rules.
        execution: ExecutionModel. ``ExecutionModel(sink=PortfolioSink())``
            for backtest, ``ExecutionModel(sink=BrokerSink(broker))`` for live.

    Validation runs in __post_init__: empty alpha list or duplicate names
    raise immediately so misconfigurations surface before a backtest
    starts.
    """

    alphas: list[AlphaModel]
    portfolio_construction: PortfolioConstructor
    risk_management: RiskManagementModel
    execution: ExecutionModel

    # Reason: ``lookback`` across all alphas — engines use this to set warmup.
    max_lookback: int = field(init=False)

    def __post_init__(self) -> None:
        if not self.alphas:
            raise ValueError("Algorithm requires at least one AlphaModel.")

        _require_unique_alpha_names(self.alphas)

        self.max_lookback = max(alpha.lookback for alpha in self.alphas)
