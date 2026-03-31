"""RSI(2) Mean Reversion strategy optimized for intraday timeframes.

Based on the Connors RSI(2) approach: enters on extreme RSI readings
(oversold/overbought) filtered by a trend SMA, exits when price reverts
to a short-term SMA.

Parameters tuned for 15-minute bars:
- RSI period: 2 (hyper-sensitive to short-term moves)
- Trend SMA: 200 (~8 trading days on 15-min bars)
- Exit SMA: 5 (~75 minutes on 15-min bars)
"""

import warnings

from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.strategies.rsi_mean_reversion.indicators import (
    RSIMeanReversionIndicatorSuite,
)
from prophitai_algo_trading.strategies.rsi_mean_reversion.signal_model import (
    RSIMeanReversionSignalModel,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class RSIMeanReversion(BaseComposableStrategy):
    """Mean reversion strategy using RSI(2) with SMA trend filter.

    Args:
        rsi_period: RSI lookback period.
        trend_sma_period: Trend filter SMA period.
        exit_sma_period: Exit trigger SMA period.
        rsi_oversold: RSI threshold for long entry.
        rsi_overbought: RSI threshold for short entry.
    """

    def __init__(
        self,
        rsi_period: int = 2,
        trend_sma_period: int = 200,
        exit_sma_period: int = 5,
        rsi_oversold: float = 10,
        rsi_overbought: float = 90,
    ):
        self.rsi_period = rsi_period
        self.trend_sma_period = trend_sma_period
        self.exit_sma_period = exit_sma_period
        self.rsi_oversold_threshold = rsi_oversold
        self.rsi_overbought_threshold = rsi_overbought
        super().__init__(
            indicator_suite=RSIMeanReversionIndicatorSuite(
                rsi_period=rsi_period,
                trend_sma_period=trend_sma_period,
                exit_sma_period=exit_sma_period,
            ),
            signal_model=RSIMeanReversionSignalModel(
                rsi_oversold_threshold=rsi_oversold,
                rsi_overbought_threshold=rsi_overbought,
            ),
        )

    @property
    def min_bars_required(self) -> int:
        """Trend SMA needs the longest lookback."""
        return self.trend_sma_period
