"""Strategy factories for the hourly multi-alpha example."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from prophitai_algo_trading import Algorithm, VectorAlgorithm
from prophitai_algo_trading.alpha_signals.intraday import (
    CloseDriftAlpha,
    CrossSectionalHourlyReversalAlpha,
    CrossSectionalHourlyVolumeAlpha,
    HourlyATRBreakoutAlpha,
    HourlyBollingerAlpha,
    HourlyRSIAlpha,
    LunchReversalAlpha,
    MicroMomentumAlpha,
    OpeningHourMomentumAlpha,
    VolumeSpikeContinuationAlpha,
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortConstructor,
    MultiAlphaBlender,
)
from prophitai_algo_trading.execution import BrokerSink, ExecutionModel, PortfolioSink
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxGrossExposureRiskModel,
    PortfolioDrawdownLimit,
    StopLossExit,
    TrailingStopExit,
)

from custom_alphas import (
    EarlySessionRangeFadeAlpha,
    IntradayTrendPersistenceAlpha,
    OpeningGapContinuationAlpha,
    RelativeVolumeReversalAlpha,
)
from custom_risk import IntradayDrawdownKillSwitch, PositionAgeExit


INITIAL_CAPITAL = 1_000_000.0
GROSS_EXPOSURE = 1.5
PER_POSITION_CAP = 0.05
QUANTILE = 0.20
MIN_ABS_SCORE = 0.05
REBALANCE_EVERY = timedelta(weeks=1)
COST_PER_TURNOVER = 0.0001
MIN_CHANGE_PCT = 0.005


def build_alphas() -> list[Any]:
    """Return fresh alpha instances for this strategy."""
    return [
        OpeningHourMomentumAlpha(),
        LunchReversalAlpha(),
        CloseDriftAlpha(),
        MicroMomentumAlpha(),
        HourlyRSIAlpha(),
        HourlyBollingerAlpha(),
        HourlyATRBreakoutAlpha(),
        VolumeSpikeContinuationAlpha(),
        CrossSectionalHourlyReversalAlpha(),
        CrossSectionalHourlyVolumeAlpha(),
        OpeningGapContinuationAlpha(),
        EarlySessionRangeFadeAlpha(),
        IntradayTrendPersistenceAlpha(),
        RelativeVolumeReversalAlpha(),
    ]


def build_alpha_weights(alphas: list[Any]) -> dict[str, float]:
    """Equal-weight every alpha until research justifies reweighting."""
    weight = 1.0 / len(alphas)

    return {alpha.name: weight for alpha in alphas}


def build_single_alpha_pcm() -> MagnitudeWeightedLongShortConstructor:
    """Fresh constructor for isolated alpha research runs."""
    return MagnitudeWeightedLongShortConstructor(
        gross_exposure=GROSS_EXPOSURE,
        per_position_cap=PER_POSITION_CAP,
        quantile=QUANTILE,
        min_abs_score=MIN_ABS_SCORE,
        rebalance_every=REBALANCE_EVERY,
    )


def build_portfolio_construction(alphas: list[Any]) -> MultiAlphaBlender:
    """Weekly-rebalanced blended long/short portfolio constructor."""
    return MultiAlphaBlender(
        weights=build_alpha_weights(alphas),
        inner=build_single_alpha_pcm(),
    )


def build_risk_model() -> CompositeRiskModel:
    """Event/live risk stack. Risk still runs on every hourly bar."""
    return CompositeRiskModel([
        IntradayDrawdownKillSwitch(loss_pct=0.03),
        PortfolioDrawdownLimit(dd_pct=0.15),
        StopLossExit(pct=0.05),
        TrailingStopExit(pct=0.08),
        PositionAgeExit(max_bars=70, max_duration=timedelta(days=14)),
        MaxGrossExposureRiskModel(max_gross=GROSS_EXPOSURE),
    ])


def build_vector_algorithm() -> VectorAlgorithm:
    """Fast vectorized strategy for research and parameter sweeps."""
    alphas = build_alphas()

    return VectorAlgorithm(
        alphas=alphas,
        pcm=build_portfolio_construction(alphas),
        initial_capital=INITIAL_CAPITAL,
        cost_per_turnover=COST_PER_TURNOVER,
    )


def build_event_algorithm() -> Algorithm:
    """Production-realistic event strategy using an in-memory portfolio sink."""
    alphas = build_alphas()

    return Algorithm(
        alphas=alphas,
        portfolio_construction=build_portfolio_construction(alphas),
        risk_management=build_risk_model(),
        execution=ExecutionModel(
            sink=PortfolioSink(),
            min_change_pct=MIN_CHANGE_PCT,
        ),
    )


def build_live_algorithm(broker) -> Algorithm:
    """Live/paper strategy using broker-backed execution."""
    alphas = build_alphas()

    return Algorithm(
        alphas=alphas,
        portfolio_construction=build_portfolio_construction(alphas),
        risk_management=build_risk_model(),
        execution=ExecutionModel(
            sink=BrokerSink(broker),
            min_change_pct=MIN_CHANGE_PCT,
        ),
    )
