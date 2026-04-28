"""``VectorAlgorithm`` — research-spec config for the vector engine.

A research spec, not a production spec: only ``alphas`` and ``pcm``
are required. There is no risk model, no execution model, no per-bar
state — those concepts belong to the event-driven ``Algorithm``.

The same alpha and PCM *instances* can be referenced from both
``Algorithm`` (event-driven) and ``VectorAlgorithm`` (vectorized) when
graduating a strategy from rapid iteration to execution-realistic
validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPortfolioConstructor


#     ================================
# --> Helper funcs
#     ================================

def _require_unique_alpha_names(alphas: list[VectorAlpha]) -> None:
    """Raise if two alphas share a ``name`` — multi-alpha PCMs key on it."""
    seen: set[str] = set()
    duplicates: list[str] = []

    for alpha in alphas:
        if alpha.name in seen:
            duplicates.append(alpha.name)
            continue

        seen.add(alpha.name)

    if duplicates:
        raise ValueError(
            f"Duplicate VectorAlpha names: {sorted(set(duplicates))}. "
            "Each alpha must have a unique ``name`` — multi-alpha "
            "PCMs partition score panels by alpha name.",
        )


#     ================================
# --> Vector algorithm
#     ================================

@dataclass
class VectorAlgorithm:
    """Composed research spec consumed by ``VectorBacktest``.

    Attributes:
        alphas: One or more vectorized alphas — each must implement
            ``compute_panel(panel) -> DataFrame``. Names must be unique.
        pcm: Single vectorized PCM that maps
            ``{alpha_name: score_panel}`` to a weight panel.
        initial_capital: Notional starting equity. Equity curve is
            scaled by this; metrics are scale-invariant.
        cost_per_turnover: Linear turnover penalty applied each bar:
            ``returns -= |weights.diff()|.sum(axis=1) * cost_per_turnover``.
            Set to 0.0 for a frictionless run.
    """

    alphas: list[VectorAlpha]
    pcm: VectorPortfolioConstructor
    initial_capital: float = 1_000_000.0
    cost_per_turnover: float = 0.0

    # Reason: surfaced for engine + tooling; computed once in __post_init__.
    alpha_names: list[str] = field(init=False)

    def __post_init__(self) -> None:
        if not self.alphas:
            raise ValueError("VectorAlgorithm requires at least one alpha.")

        _require_unique_alpha_names(self.alphas)

        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")

        if self.cost_per_turnover < 0:
            raise ValueError("cost_per_turnover must be >= 0")

        self.alpha_names = [a.name for a in self.alphas]
