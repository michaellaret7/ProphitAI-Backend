"""Algorithm composer — wires alphas, PCM, risk, and execution.

The 8-alpha stack (weights sum to 1.00):

    rsi_reversion        0.12    PerSymbolAlpha       — short-horizon mean rev
    bollinger_reversion  0.12    PerSymbolAlpha       — 20-day band mean rev
    atr_momentum         0.14    PerSymbolAlpha       — vol-adjusted momentum
    macd_histogram       0.12    PerSymbolAlpha       — trend-following
    overnight_gap        0.08    PerSymbolAlpha       — gap persistence
    liquidity_tilt       0.08    CrossSectionalAlpha  — $-volume tilt
    rs_rank              0.14    CrossSectionalAlpha  — 3M return rank
    cointegration_pair   0.20    PairAlpha            — stat arb (built-in)

Blend = ``MultiAlphaBlendPCM`` (z-scores per alpha, weighted sum)
feeding a ``MagnitudeWeightedLongShortPCM`` that converts blended
scores into dollar-neutral target shares at 1.5x gross exposure with
a 6% per-position cap (tighter than before because the 150-ticker
universe can absorb more names without concentration).

Risk stack (in order): drawdown delever -> tightened stop-loss ->
time-stop (max 5 bars) -> gross-exposure cap. Tightened from the
original 8% stop after attribution analysis showed per-stop avg loss
of -$2,800; TimeStop added because magnitude_decay exits past 4 days
bleed (-$41 avg) while 1-day exits were profitable (+$12 avg).

Execution = ``ExecutionModel(sink=PortfolioSink())`` for backtests.
"""

from __future__ import annotations

from prophitai_algo_trading.alphas import CointegrationPairAlpha
from prophitai_algo_trading.core.algorithm import Algorithm
from prophitai_algo_trading.execution import ExecutionModel, PortfolioSink
from prophitai_algo_trading.portfolio_construction import (
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    StopLossExit,
    TimeStop,
)

from .alphas import (
    ATRNormalizedMomentumAlpha,
    BollingerBandReversionAlpha,
    DollarVolumeRankAlpha,
    MACDHistogramAlpha,
    OvernightGapAlpha,
    RelativeStrengthRankAlpha,
    RSIMeanReversionAlpha,
)
from .universe import SECTOR_PAIRS


#     ================================
# --> Algorithm factory
#     ================================

def build_algorithm() -> Algorithm:
    """Construct the fully-composed 8-alpha long/short algorithm."""
    return Algorithm(
        alphas=[
            RSIMeanReversionAlpha(),
            BollingerBandReversionAlpha(),
            ATRNormalizedMomentumAlpha(),
            MACDHistogramAlpha(),
            OvernightGapAlpha(),
            DollarVolumeRankAlpha(),
            RelativeStrengthRankAlpha(),
            CointegrationPairAlpha(
                pairs=SECTOR_PAIRS,
                lookback_days=60,
                hold_days=10,
                entry_z=2.0,
                max_z=4.0,
            ),
        ],
        portfolio_construction=MultiAlphaBlendPCM(
            weights={
                "rsi_reversion":       0.12,
                "bollinger_reversion": 0.12,
                "atr_momentum":        0.14,
                "macd_histogram":      0.12,
                "overnight_gap":       0.08,
                "liquidity_tilt":      0.08,
                "rs_rank":             0.14,
                "cointegration_pair":  0.20,
            },
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5,
                per_position_cap=0.06,
                quantile=0.15,
                min_abs_score=0.10,
            ),
        ),
        risk_management=CompositeRiskModel([
            MaxDrawdownRiskModel(
                max_drawdown_pct=0.15,
                delever_factor=0.5,
                cooldown_days=30,
            ),
            StopLossExit(pct=0.04),
            TimeStop(max_bars=5),
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),
        execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
    )
