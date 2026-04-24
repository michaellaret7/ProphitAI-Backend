"""Algorithm composer — wires alphas, PCM, risk, and execution.

The 5-alpha stack:

    rsi_reversion        0.20    (PerSymbolAlpha)
    bollinger_reversion  0.20    (PerSymbolAlpha)
    atr_momentum         0.25    (PerSymbolAlpha)
    liquidity_tilt       0.10    (CrossSectionalAlpha)
    cointegration_pair   0.25    (PairAlpha, built-in)

Blend = ``MultiAlphaBlendPCM`` (z-scores per alpha, weighted sum)
feeding a ``MagnitudeWeightedLongShortPCM`` that converts blended
scores into dollar-neutral target shares at 1.5x gross exposure with
an 8% per-position cap.

Risk stack (in order): drawdown delever -> stop-loss forced exit ->
gross-exposure cap. Order matters — portfolio-wide circuit breakers
before position-level stops before final gross guard.

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
)

from .alphas import (
    ATRNormalizedMomentumAlpha,
    BollingerBandReversionAlpha,
    DollarVolumeRankAlpha,
    RSIMeanReversionAlpha,
)
from .universe import SECTOR_PAIRS


#     ================================
# --> Algorithm factory
#     ================================

def build_algorithm() -> Algorithm:
    """Construct the fully-composed 5-alpha long/short algorithm."""
    return Algorithm(
        alphas=[
            RSIMeanReversionAlpha(),
            BollingerBandReversionAlpha(),
            ATRNormalizedMomentumAlpha(),
            DollarVolumeRankAlpha(),
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
                "rsi_reversion":       0.20,
                "bollinger_reversion": 0.20,
                "atr_momentum":        0.25,
                "liquidity_tilt":      0.10,
                "cointegration_pair":  0.25,
            },
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5,
                per_position_cap=0.08,
                quantile=0.20,
                min_abs_score=0.10,
            ),
        ),
        risk_management=CompositeRiskModel([
            MaxDrawdownRiskModel(
                max_drawdown_pct=0.15,
                delever_factor=0.5,
                cooldown_days=30,
            ),
            StopLossExit(pct=0.08),
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),
        execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
    )
