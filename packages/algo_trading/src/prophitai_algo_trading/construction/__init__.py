"""Built-in PortfolioConstructionModels — Insights → PortfolioTargets.

Four primitives covering the common cases:

    EqualWeightPCM            top-N equal-weight by |signed score|
    InsightWeightedPCM        magnitude-proportional, per-position cap
    MagnitudeWeightedLongShortPCM   decile-cut dollar-neutral L/S
    MultiAlphaBlendPCM        z-score per alpha, weighted blend → inner PCM

All four satisfy the ``PortfolioConstructionModel`` protocol. Compose as
needed — MultiAlphaBlendPCM nests another PCM as its ``inner``.
"""

from prophitai_algo_trading.construction.equal_weight import (
    EqualWeightPCM,
)
from prophitai_algo_trading.construction.insight_weighted import (
    InsightWeightedPCM,
)
from prophitai_algo_trading.construction.magnitude_ls import (
    MagnitudeWeightedLongShortPCM,
)
from prophitai_algo_trading.construction.multi_alpha_blend import (
    MultiAlphaBlendPCM,
)

__all__ = [
    "EqualWeightPCM",
    "InsightWeightedPCM",
    "MagnitudeWeightedLongShortPCM",
    "MultiAlphaBlendPCM",
]
