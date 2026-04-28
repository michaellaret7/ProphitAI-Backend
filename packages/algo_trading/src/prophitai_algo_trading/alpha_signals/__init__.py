"""Built-in ``AlphaModel`` implementations plus the shared base classes.

Every alpha satisfies the ``AlphaModel`` protocol (``name``, ``lookback``,
``update(ctx) -> list[Insight]``). New alphas should subclass one of
the three bases below rather than implement ``update`` from scratch;
the base owns Insight construction so the per-alpha contract stays
consistent across the framework.

Base classes (pick the one that matches your signal's semantics):

    PerSymbolAlpha
        Score each ticker from its own history alone. Default choice.

    CrossSectionalAlpha
        Score each ticker against universe-wide stats (median, rank,
        percentile, z-score).

    PairAlpha
        Score ticker *pairs* for stat arb; each firing pair emits two
        Insights (long leg + short leg).

If none of the three fits, implement ``AlphaModel`` (the Protocol in
``core.protocols``) directly — inheritance is optional.

Built-in alphas, grouped by signal family:

    Trend / momentum:
        MomentumAlpha                 12-1 cross-sectional momentum
        BreakoutAlpha                 Donchian channel position
        TrendVolumeAlpha              MACD gated by volume z-score
        MovingAverageRibbonAlpha      Fast vs slow SMA spread
        AccelerationAlpha             Change in momentum (2nd derivative)
        ADXAlpha                      Wilder ADX × MA-cross direction
        KaufmanEfficiencyAlpha        Net change ÷ path length, signed
        FiftyTwoWeekHighAlpha         Anchoring to 252-day peak

    Mean reversion / oscillators:
        ShortTermReversalAlpha        Negated 5-day return
        RSIAlpha                      Wilder RSI mean-reversion
        DispersionReversalAlpha       Universe-z-score reversal
        GapFadeAlpha                  Negated overnight gaps
        StochasticOscillatorAlpha     Lane %K mean-reversion
        ConnorsRSIAlpha               RSI + streak + percent-rank
        IntradayReversalAlpha         Negated open-to-close return

    Volatility / squeeze / risk:
        LowVolAlpha                   Cross-sectional low-vol anomaly
        RangeCompressionAlpha         ATR-ratio squeeze, signed
        GarmanKlassVolAlpha           OHLC vol estimator (low long)
        LotteryAlpha                  Negated MAX-N-day return
        VolOfVolAlpha                 Stable-vol-regime premium
        SkewnessAlpha                 Negated rolling skew
        IdiosyncraticVolAlpha         Residual vol after market beta
        BetaToMarketAlpha             BAB — short high beta

    Volume / flow:
        VolumeShockAlpha              Volume z × recent return
        OBVSlopeAlpha                 Cumulative signed-volume slope
        ChaikinMoneyFlowAlpha         Volume-weighted CLV
        AccumulationDistributionAlpha A/D vs price slope divergence
        AmihudIlliquidityAlpha        |return|/dollar-volume premium

    Range / candle structure:
        CloseLocationAlpha            Rolling-mean of CLV
        NarrowRange7Alpha             Crabel NR7 pre-breakout pattern
        OvernightDriftAlpha           Sum of overnight returns

    Calendar:
        TurnOfMonthAlpha              Last-day + first-3-days seasonality

    Stat arb:
        CointegrationPairAlpha        Pair-trade on cointegrated tickers
"""

from prophitai_algo_trading.alpha_signals.acceleration import AccelerationAlpha
from prophitai_algo_trading.alpha_signals.accumulation_distribution import (
    AccumulationDistributionAlpha,
)
from prophitai_algo_trading.alpha_signals.adx import ADXAlpha
from prophitai_algo_trading.alpha_signals.amihud_illiquidity import (
    AmihudIlliquidityAlpha,
)
from prophitai_algo_trading.alpha_signals.base import (
    CrossSectionalAlpha,
    PairAlpha,
    PerSymbolAlpha,
)
from prophitai_algo_trading.alpha_signals.beta_to_market import BetaToMarketAlpha
from prophitai_algo_trading.alpha_signals.breakout import BreakoutAlpha
from prophitai_algo_trading.alpha_signals.chaikin_money_flow import (
    ChaikinMoneyFlowAlpha,
)
from prophitai_algo_trading.alpha_signals.close_location import CloseLocationAlpha
from prophitai_algo_trading.alpha_signals.cointegration_pair import (
    CointegrationPairAlpha,
)
from prophitai_algo_trading.alpha_signals.connors_rsi import ConnorsRSIAlpha
from prophitai_algo_trading.alpha_signals.dispersion_reversal import (
    DispersionReversalAlpha,
)
from prophitai_algo_trading.alpha_signals.efficiency_ratio import (
    KaufmanEfficiencyAlpha,
)
from prophitai_algo_trading.alpha_signals.fifty_two_week_high import (
    FiftyTwoWeekHighAlpha,
)
from prophitai_algo_trading.alpha_signals.gap_fade import GapFadeAlpha
from prophitai_algo_trading.alpha_signals.garman_klass import GarmanKlassVolAlpha
from prophitai_algo_trading.alpha_signals.idiosyncratic_vol import (
    IdiosyncraticVolAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday_reversal import (
    IntradayReversalAlpha,
)
from prophitai_algo_trading.alpha_signals.lottery import LotteryAlpha
from prophitai_algo_trading.alpha_signals.low_vol import LowVolAlpha
from prophitai_algo_trading.alpha_signals.ma_ribbon import (
    MovingAverageRibbonAlpha,
)
from prophitai_algo_trading.alpha_signals.momentum import MomentumAlpha
from prophitai_algo_trading.alpha_signals.nr7 import NarrowRange7Alpha
from prophitai_algo_trading.alpha_signals.obv_slope import OBVSlopeAlpha
from prophitai_algo_trading.alpha_signals.overnight_drift import (
    OvernightDriftAlpha,
)
from prophitai_algo_trading.alpha_signals.range_compression import (
    RangeCompressionAlpha,
)
from prophitai_algo_trading.alpha_signals.reversal import ShortTermReversalAlpha
from prophitai_algo_trading.alpha_signals.rsi import RSIAlpha
from prophitai_algo_trading.alpha_signals.skewness import SkewnessAlpha
from prophitai_algo_trading.alpha_signals.stochastic import (
    StochasticOscillatorAlpha,
)
from prophitai_algo_trading.alpha_signals.trend_volume import TrendVolumeAlpha
from prophitai_algo_trading.alpha_signals.turn_of_month import TurnOfMonthAlpha
from prophitai_algo_trading.alpha_signals.vol_of_vol import VolOfVolAlpha
from prophitai_algo_trading.alpha_signals.volume_shock import VolumeShockAlpha

__all__ = [
    # Base classes (for agent-authored alphas)
    "CrossSectionalAlpha",
    "PairAlpha",
    "PerSymbolAlpha",
    # Built-in alphas — alphabetized
    "ADXAlpha",
    "AccelerationAlpha",
    "AccumulationDistributionAlpha",
    "AmihudIlliquidityAlpha",
    "BetaToMarketAlpha",
    "BreakoutAlpha",
    "ChaikinMoneyFlowAlpha",
    "CloseLocationAlpha",
    "CointegrationPairAlpha",
    "ConnorsRSIAlpha",
    "DispersionReversalAlpha",
    "FiftyTwoWeekHighAlpha",
    "GapFadeAlpha",
    "GarmanKlassVolAlpha",
    "IdiosyncraticVolAlpha",
    "IntradayReversalAlpha",
    "KaufmanEfficiencyAlpha",
    "LotteryAlpha",
    "LowVolAlpha",
    "MomentumAlpha",
    "MovingAverageRibbonAlpha",
    "NarrowRange7Alpha",
    "OBVSlopeAlpha",
    "OvernightDriftAlpha",
    "RSIAlpha",
    "RangeCompressionAlpha",
    "ShortTermReversalAlpha",
    "SkewnessAlpha",
    "StochasticOscillatorAlpha",
    "TrendVolumeAlpha",
    "TurnOfMonthAlpha",
    "VolOfVolAlpha",
    "VolumeShockAlpha",
]
