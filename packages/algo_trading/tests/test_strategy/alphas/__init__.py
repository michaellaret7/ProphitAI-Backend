"""Custom alphas for the multi-factor strategy.

Each file holds exactly one alpha class. All subclass a base from
``prophitai_algo_trading.alphas.base`` — the base owns Insight
construction so each alpha implements only its scoring math.

    rsi_reversion.py          RSIMeanReversionAlpha        (PerSymbolAlpha)
    bollinger_reversion.py    BollingerBandReversionAlpha  (PerSymbolAlpha)
    atr_momentum.py           ATRNormalizedMomentumAlpha   (PerSymbolAlpha)
    dollar_volume_rank.py     DollarVolumeRankAlpha        (CrossSectionalAlpha)
"""

from .atr_momentum import ATRNormalizedMomentumAlpha
from .bollinger_reversion import BollingerBandReversionAlpha
from .dollar_volume_rank import DollarVolumeRankAlpha
from .rsi_reversion import RSIMeanReversionAlpha

__all__ = [
    "ATRNormalizedMomentumAlpha",
    "BollingerBandReversionAlpha",
    "DollarVolumeRankAlpha",
    "RSIMeanReversionAlpha",
]
