"""Built-in portfolio constructors and the multi-alpha blender.

Three constructors + one blender, covering the common cases:

    EqualWeightConstructor               top-N equal-weight by |signed score|
    InsightWeightedConstructor           magnitude-proportional, per-position cap
    MagnitudeWeightedLongShortConstructor   decile-cut dollar-neutral L/S
    MultiAlphaBlender                    z-score per alpha, weighted blend → inner constructor

Constructors satisfy the ``PortfolioConstructor`` protocol; the blender
satisfies ``SignalBlender``. Compose as needed — ``MultiAlphaBlender``
nests a ``PortfolioConstructor`` as its ``inner``.
"""

from prophitai_algo_trading.construction.equal_weight import (
    EqualWeightConstructor,
)
from prophitai_algo_trading.construction.insight_weighted import (
    InsightWeightedConstructor,
)
from prophitai_algo_trading.construction.magnitude_ls import (
    MagnitudeWeightedLongShortConstructor,
)
from prophitai_algo_trading.construction.multi_alpha_blend import (
    MultiAlphaBlender,
)

__all__ = [
    "EqualWeightConstructor",
    "InsightWeightedConstructor",
    "MagnitudeWeightedLongShortConstructor",
    "MultiAlphaBlender",
]
