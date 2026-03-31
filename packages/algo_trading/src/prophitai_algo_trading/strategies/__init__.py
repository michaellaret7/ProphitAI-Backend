"""Strategy contracts and in-repo strategy packages.

Scaffold-only packages such as ``template`` live under this namespace but are
not re-exported here as production strategy defaults.
"""

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy

__all__ = [
    "BaseStrategy",
    "BaseComposableStrategy",
]
