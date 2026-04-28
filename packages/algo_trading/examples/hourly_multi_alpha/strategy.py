"""Strategy factories for the hourly multi-alpha example."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class HourlyMultiAlphaConfig:
    """Tunable parameters for the hourly multi-alpha strategy."""

    initial_capital: float = 1_000_000.0
    gross_exposure: float = 1.5
    per_position_cap: float = 0.05
    quantile: float = 0.20
    min_abs_score: float = 0.05
    rebalance_every: timedelta = timedelta(weeks=1)
    cost_per_turnover: float = 0.0001
    min_change_pct: float = 0.005


DEFAULT_CONFIG = HourlyMultiAlphaConfig()

INITIAL_CAPITAL = DEFAULT_CONFIG.initial_capital
GROSS_EXPOSURE = DEFAULT_CONFIG.gross_exposure
PER_POSITION_CAP = DEFAULT_CONFIG.per_position_cap
QUANTILE = DEFAULT_CONFIG.quantile
MIN_ABS_SCORE = DEFAULT_CONFIG.min_abs_score
REBALANCE_EVERY = DEFAULT_CONFIG.rebalance_every
COST_PER_TURNOVER = DEFAULT_CONFIG.cost_per_turnover


class HourlyMultiAlphaStrategy:
    """Standard strategy builder for research, backtest, and live modes."""

    def __init__(self, config: HourlyMultiAlphaConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG

    def build_alphas(self) -> list[Any]:
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

    def build_alpha_weights(self, alphas: list[Any]) -> dict[str, float]:
        """Equal-weight every alpha until research justifies reweighting."""
        weight = 1.0 / len(alphas)

        return {alpha.name: weight for alpha in alphas}

    def build_single_alpha_pcm(self) -> MagnitudeWeightedLongShortConstructor:
        """Fresh constructor for isolated alpha research runs."""
        return MagnitudeWeightedLongShortConstructor(
            gross_exposure=self.config.gross_exposure,
            per_position_cap=self.config.per_position_cap,
            quantile=self.config.quantile,
            min_abs_score=self.config.min_abs_score,
            rebalance_every=self.config.rebalance_every,
        )

    def build_portfolio_construction(self, alphas: list[Any]) -> MultiAlphaBlender:
        """Weekly-rebalanced blended long/short portfolio constructor."""
        return MultiAlphaBlender(
            weights=self.build_alpha_weights(alphas),
            inner=self.build_single_alpha_pcm(),
        )

    def build_risk_model(self) -> CompositeRiskModel:
        """Event/live risk stack. Risk still runs on every hourly bar."""
        return CompositeRiskModel([
            IntradayDrawdownKillSwitch(loss_pct=0.03),
            PortfolioDrawdownLimit(dd_pct=0.15),
            StopLossExit(pct=0.05),
            TrailingStopExit(pct=0.08),
            PositionAgeExit(max_bars=70, max_duration=timedelta(days=14)),
            MaxGrossExposureRiskModel(max_gross=self.config.gross_exposure),
        ])

    def build_vector_algorithm(self) -> VectorAlgorithm:
        """Fast vectorized strategy for research and parameter sweeps."""
        alphas = self.build_alphas()

        return VectorAlgorithm(
            alphas=alphas,
            pcm=self.build_portfolio_construction(alphas),
            initial_capital=self.config.initial_capital,
            cost_per_turnover=self.config.cost_per_turnover,
        )

    def build_event_algorithm(self) -> Algorithm:
        """Production-realistic event strategy using an in-memory portfolio sink."""
        alphas = self.build_alphas()

        return Algorithm(
            alphas=alphas,
            portfolio_construction=self.build_portfolio_construction(alphas),
            risk_management=self.build_risk_model(),
            execution=ExecutionModel(
                sink=PortfolioSink(),
                min_change_pct=self.config.min_change_pct,
            ),
        )

    def build_live_algorithm(self, broker) -> Algorithm:
        """Live/paper strategy using broker-backed execution."""
        alphas = self.build_alphas()

        return Algorithm(
            alphas=alphas,
            portfolio_construction=self.build_portfolio_construction(alphas),
            risk_management=self.build_risk_model(),
            execution=ExecutionModel(
                sink=BrokerSink(broker),
                min_change_pct=self.config.min_change_pct,
            ),
        )


DEFAULT_STRATEGY = HourlyMultiAlphaStrategy()


def build_alphas() -> list[Any]:
    """Return fresh alpha instances for this strategy."""
    return DEFAULT_STRATEGY.build_alphas()


def build_alpha_weights(alphas: list[Any]) -> dict[str, float]:
    """Equal-weight every alpha until research justifies reweighting."""
    return DEFAULT_STRATEGY.build_alpha_weights(alphas)


def build_single_alpha_pcm() -> MagnitudeWeightedLongShortConstructor:
    """Fresh constructor for isolated alpha research runs."""
    return DEFAULT_STRATEGY.build_single_alpha_pcm()


def build_portfolio_construction(alphas: list[Any]) -> MultiAlphaBlender:
    """Weekly-rebalanced blended long/short portfolio constructor."""
    return DEFAULT_STRATEGY.build_portfolio_construction(alphas)


def build_risk_model() -> CompositeRiskModel:
    """Event/live risk stack. Risk still runs on every hourly bar."""
    return DEFAULT_STRATEGY.build_risk_model()


def build_vector_algorithm() -> VectorAlgorithm:
    """Fast vectorized strategy for research and parameter sweeps."""
    return DEFAULT_STRATEGY.build_vector_algorithm()


def build_event_algorithm() -> Algorithm:
    """Production-realistic event strategy using an in-memory portfolio sink."""
    return DEFAULT_STRATEGY.build_event_algorithm()


def build_live_algorithm(broker) -> Algorithm:
    """Live/paper strategy using broker-backed execution."""
    return DEFAULT_STRATEGY.build_live_algorithm(broker)
