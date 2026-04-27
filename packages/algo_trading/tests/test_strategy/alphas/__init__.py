"""Custom alphas for the multi-factor strategy.

Each file holds exactly one alpha class. All subclass a base from
``prophitai_algo_trading.alpha_signals.base`` — the base owns Insight
construction so each alpha implements only its scoring math.

    rsi_reversion.py           RSIMeanReversionAlpha         (PerSymbolAlpha)
    bollinger_reversion.py     BollingerBandReversionAlpha   (PerSymbolAlpha)
    atr_momentum.py            ATRNormalizedMomentumAlpha    (PerSymbolAlpha)
    macd_histogram.py          MACDHistogramAlpha            (PerSymbolAlpha)
    overnight_gap.py           OvernightGapAlpha             (PerSymbolAlpha)
    dollar_volume_rank.py      DollarVolumeRankAlpha         (CrossSectionalAlpha)
    rs_rank.py                 RelativeStrengthRankAlpha     (CrossSectionalAlpha)
"""

from .atr_momentum import ATRNormalizedMomentumAlpha
from .bollinger_reversion import BollingerBandReversionAlpha
from .dollar_volume_rank import DollarVolumeRankAlpha
from .macd_histogram import MACDHistogramAlpha
from .overnight_gap import OvernightGapAlpha
from .rs_rank import RelativeStrengthRankAlpha
from .rsi_reversion import RSIMeanReversionAlpha

__all__ = [
    "ATRNormalizedMomentumAlpha",
    "BollingerBandReversionAlpha",
    "DollarVolumeRankAlpha",
    "MACDHistogramAlpha",
    "OvernightGapAlpha",
    "RelativeStrengthRankAlpha",
    "RSIMeanReversionAlpha",
]
