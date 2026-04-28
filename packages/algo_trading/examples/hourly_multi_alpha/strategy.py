"""Hourly multi-alpha strategy spec.

Reading order: alphas (what signals fire) -> portfolio construction (how we
size them) -> risk (what blows positions out early) -> algorithm builders
(one per runtime mode).
"""

from __future__ import annotations

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

from alphas import (
    EarlySessionRangeFadeAlpha,
    IntradayTrendPersistenceAlpha,
    OpeningGapContinuationAlpha,
    RelativeVolumeReversalAlpha,
)
from config import Config
from risk import IntradayDrawdownKillSwitch, PositionAgeExit


# ================================
# --> Alphas
# ================================

def _alphas() -> list[Any]:
    """Fresh alpha instances, grouped by intent."""
    return [
        # Time-of-day
        OpeningHourMomentumAlpha(),
        LunchReversalAlpha(),
        CloseDriftAlpha(),
        OpeningGapContinuationAlpha(),
        EarlySessionRangeFadeAlpha(),

        # Trend / momentum
        MicroMomentumAlpha(),
        IntradayTrendPersistenceAlpha(),

        # Mean reversion
        HourlyRSIAlpha(),
        HourlyBollingerAlpha(),

        # Breakout / volume
        HourlyATRBreakoutAlpha(),
        VolumeSpikeContinuationAlpha(),
        RelativeVolumeReversalAlpha(),

        # Cross-sectional
        CrossSectionalHourlyReversalAlpha(),
        CrossSectionalHourlyVolumeAlpha(),
    ]


# ================================
# --> Portfolio construction
# ================================

def _pcm(cfg: Config) -> MagnitudeWeightedLongShortConstructor:
    return MagnitudeWeightedLongShortConstructor(
        gross_exposure=cfg.gross_exposure,
        per_position_cap=cfg.per_position_cap,
        quantile=cfg.quantile,
        min_abs_score=cfg.min_abs_score,
        rebalance_every=cfg.rebalance_every,
    )


def _blender(alphas: list[Any], cfg: Config) -> MultiAlphaBlender:
    weight = 1.0 / len(alphas)
    weights = {alpha.name: weight for alpha in alphas}

    return MultiAlphaBlender(weights=weights, inner=_pcm(cfg))


# ================================
# --> Risk
# ================================

def _risk(cfg: Config) -> CompositeRiskModel:
    return CompositeRiskModel([
        IntradayDrawdownKillSwitch(loss_pct=cfg.intraday_dd_kill),
        PortfolioDrawdownLimit(dd_pct=cfg.portfolio_dd_limit),
        StopLossExit(pct=cfg.stop_loss_pct),
        TrailingStopExit(pct=cfg.trailing_stop_pct),
        PositionAgeExit(
            max_bars=cfg.max_position_bars,
            max_duration=cfg.max_position_duration,
        ),
        MaxGrossExposureRiskModel(max_gross=cfg.gross_exposure),
    ])


# ================================
# --> Algorithm builders
# ================================




def build_research_pcm(cfg: Config = Config()) -> MagnitudeWeightedLongShortConstructor:
    """Single-alpha PCM factory for isolated alpha research."""
    return _pcm(cfg)


def build_vector_algorithm(cfg: Config = Config()) -> VectorAlgorithm:
    """Fast vectorized algorithm for sweeps and research."""
    alphas = _alphas()

    return VectorAlgorithm(
        alphas=alphas,
        pcm=_blender(alphas, cfg),
        initial_capital=cfg.initial_capital,
        cost_per_turnover=cfg.cost_per_turnover,
    )


def build_event_algorithm(cfg: Config = Config()) -> Algorithm:
    """Production-realistic event algorithm with in-memory portfolio sink."""
    alphas = _alphas()

    return Algorithm(
        alphas=alphas,
        portfolio_construction=_blender(alphas, cfg),
        risk_management=_risk(cfg),
        execution=ExecutionModel(
            sink=PortfolioSink(),
            min_change_pct=cfg.min_change_pct,
        ),
    )


def build_live_algorithm(broker, cfg: Config = Config()) -> Algorithm:
    """Live/paper algorithm using broker-backed execution."""
    alphas = _alphas()

    return Algorithm(
        alphas=alphas,
        portfolio_construction=_blender(alphas, cfg),
        risk_management=_risk(cfg),
        execution=ExecutionModel(
            sink=BrokerSink(broker),
            min_change_pct=cfg.min_change_pct,
        ),
    )
