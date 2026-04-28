"""Intraday alpha signals (hourly bar horizon).

These alphas are tuned for hourly OHLCV data — short lookbacks, hold
horizons of 1-8 hours, time-of-day and intra-session microstructure
patterns. Distinct from the parent ``alpha_signals`` package whose
defaults are calibrated for daily bars.

Categories:

    Time-of-day (4):
        OpeningHourMomentumAlpha     today's first-bar return persists
        LunchReversalAlpha           fade lunch-hour 3-bar moves
        CloseDriftAlpha              close-hour bars: ride day's drift
        HourOfDayBiasAlpha           per-hour historical mean return

    VWAP-based (2):
        SessionVWAPDeviationAlpha    fade close-vs-anchored-VWAP gap
        AnchoredVWAPBreakoutAlpha    cross-over momentum on day VWAP

    Short-horizon momentum/reversion (4):
        MicroMomentumAlpha           3-bar return continuation
        HourlyRSIAlpha               14-bar RSI mean-reversion
        OneBarReversalAlpha          negate last-bar return
        ConsecutiveBarFadeAlpha      fade 4+ same-direction streak

    Volume / flow (3):
        VolumeSpikeContinuationAlpha vol z × sign(return), floored
        HourlyOBVAlpha               cumulative signed-volume slope
        CloseLocationInBarAlpha      rolling CLV mean

    Volatility / range (2):
        HourlyATRBreakoutAlpha       1-bar move / ATR (vol-scaled)
        HourlyBollingerAlpha         0.5 - %B mean-reversion

    Cross-sectional (2):
        CrossSectionalHourlyReversalAlpha   row-z negate
        CrossSectionalHourlyVolumeAlpha     row-z dollar volume × sign

    Pattern (1):
        RangeBreakoutHourlyAlpha     +1 on N-bar high, -1 on N-bar low
"""

from prophitai_algo_trading.alpha_signals.intraday.anchored_vwap_breakout import (
    AnchoredVWAPBreakoutAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.close_drift import (
    CloseDriftAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.close_location_in_bar import (
    CloseLocationInBarAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.consecutive_bar_fade import (
    ConsecutiveBarFadeAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.cross_sectional_hourly_reversal import (
    CrossSectionalHourlyReversalAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.cross_sectional_hourly_volume import (
    CrossSectionalHourlyVolumeAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.hour_of_day_bias import (
    HourOfDayBiasAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.hourly_atr_breakout import (
    HourlyATRBreakoutAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.hourly_bollinger import (
    HourlyBollingerAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.hourly_obv import (
    HourlyOBVAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.hourly_rsi import (
    HourlyRSIAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.lunch_reversal import (
    LunchReversalAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.micro_momentum import (
    MicroMomentumAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.one_bar_reversal import (
    OneBarReversalAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.opening_hour_momentum import (
    OpeningHourMomentumAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.range_breakout_hourly import (
    RangeBreakoutHourlyAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.session_vwap_deviation import (
    SessionVWAPDeviationAlpha,
)
from prophitai_algo_trading.alpha_signals.intraday.volume_spike_continuation import (
    VolumeSpikeContinuationAlpha,
)

__all__ = [
    "AnchoredVWAPBreakoutAlpha",
    "CloseDriftAlpha",
    "CloseLocationInBarAlpha",
    "ConsecutiveBarFadeAlpha",
    "CrossSectionalHourlyReversalAlpha",
    "CrossSectionalHourlyVolumeAlpha",
    "HourOfDayBiasAlpha",
    "HourlyATRBreakoutAlpha",
    "HourlyBollingerAlpha",
    "HourlyOBVAlpha",
    "HourlyRSIAlpha",
    "LunchReversalAlpha",
    "MicroMomentumAlpha",
    "OneBarReversalAlpha",
    "OpeningHourMomentumAlpha",
    "RangeBreakoutHourlyAlpha",
    "SessionVWAPDeviationAlpha",
    "VolumeSpikeContinuationAlpha",
]
