"""Orchestrator for computing all technical indicators on a single ticker's OHLCV data."""

import pandas as pd

from app.core.calc_v2.models.technicals import (
    MomentumTechnicals,
    StatisticalTechnicals,
    TickerTechnicals,
    TrendTechnicals,
    VolatilityTechnicals,
    VolumeTechnicals,
)
from app.core.calc_v2.technicals.momentum import (
    calc_adx,
    calc_macd,
    calc_momentum_acceleration,
    calc_roc,
    calc_rsi,
    calc_time_series_momentum,
)
from app.core.calc_v2.technicals.statistical import (
    calc_autocorrelation,
    calc_z_score,
)
from app.core.calc_v2.technicals.trend import (
    calc_ema,
    calc_ichimoku,
    calc_linear_regression,
    calc_sma,
)
from app.core.calc_v2.technicals.volatility import (
    calc_atr,
    calc_bollinger_bands,
    calc_bollinger_bandwidth,
    calc_bollinger_pct_b,
    calc_close_to_close_volatility,
    calc_donchian_channels,
    calc_garman_klass_volatility,
    calc_keltner_channels,
    calc_parkinson_volatility,
    calc_yang_zhang_volatility,
)
from app.core.calc_v2.technicals.volume import (
    calc_accumulation_distribution,
    calc_amihud_illiquidity,
    calc_cmf,
    calc_mfi,
    calc_obv,
    calc_vwap,
    calc_vwma,
)


def calc_trend(ohlcv: pd.DataFrame) -> TrendTechnicals:
    """Calculate all trend indicators.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
    """
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["adj_close"]
    slope, r_squared = calc_linear_regression(close, window=50)
    tenkan, kijun, senkou_a, senkou_b, chikou = calc_ichimoku(high, low, close)

    return TrendTechnicals(
        sma_20=calc_sma(close, window=20),
        sma_50=calc_sma(close, window=50),
        sma_200=calc_sma(close, window=200),
        ema_12=calc_ema(close, span=12),
        ema_26=calc_ema(close, span=26),
        ema_50=calc_ema(close, span=50),
        ema_200=calc_ema(close, span=200),
        linreg_slope_50=slope,
        linreg_r_squared_50=r_squared,
        ichimoku_tenkan=tenkan,
        ichimoku_kijun=kijun,
        ichimoku_senkou_a=senkou_a,
        ichimoku_senkou_b=senkou_b,
        ichimoku_chikou=chikou,
    )


def calc_momentum(ohlcv: pd.DataFrame) -> MomentumTechnicals:
    """Calculate all momentum indicators.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
    """
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["adj_close"]
    macd_line, macd_signal, macd_histogram = calc_macd(close)

    return MomentumTechnicals(
        roc_12m=calc_roc(close, window=252, skip_recent=21),
        rsi_14=calc_rsi(close, window=14),
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        adx_14=calc_adx(high, low, close, window=14),
        time_series_momentum=calc_time_series_momentum(close),
        momentum_acceleration=calc_momentum_acceleration(close),
    )


def calc_volatility(ohlcv: pd.DataFrame) -> VolatilityTechnicals:
    """Calculate all volatility indicators.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
    """
    # Reason: range-based vol estimators use raw OHLC because intraday ratios
    # (H/L, C/O) are split-invariant within a single day.
    open_ = ohlcv["open"]
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["adj_close"]
    bollinger_upper, bollinger_middle, bollinger_lower = calc_bollinger_bands(close)
    donchian_upper, donchian_middle, donchian_lower = calc_donchian_channels(high, low)
    keltner_upper, keltner_middle, keltner_lower = calc_keltner_channels(high, low, close)

    return VolatilityTechnicals(
        atr_14=calc_atr(high, low, close, window=14),
        close_to_close_vol_20=calc_close_to_close_volatility(close, window=20),
        parkinson_vol_20=calc_parkinson_volatility(high, low, window=20),
        garman_klass_vol_20=calc_garman_klass_volatility(open_, high, low, close, window=20),
        yang_zhang_vol_20=calc_yang_zhang_volatility(open_, high, low, close, window=20),
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        bollinger_pct_b=calc_bollinger_pct_b(close),
        bollinger_bandwidth=calc_bollinger_bandwidth(close),
        donchian_upper=donchian_upper,
        donchian_middle=donchian_middle,
        donchian_lower=donchian_lower,
        keltner_upper=keltner_upper,
        keltner_middle=keltner_middle,
        keltner_lower=keltner_lower,
    )


def calc_volume(ohlcv: pd.DataFrame) -> VolumeTechnicals:
    """Calculate all volume and liquidity indicators.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
    """
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["adj_close"]
    volume = ohlcv["volume"]

    return VolumeTechnicals(
        obv=calc_obv(close, volume),
        vwma_20=calc_vwma(close, volume, window=20),
        vwap_20=calc_vwap(high, low, close, volume, window=20),
        cmf_20=calc_cmf(high, low, close, volume, window=20),
        accumulation_distribution=calc_accumulation_distribution(high, low, close, volume),
        mfi_14=calc_mfi(high, low, close, volume, window=14),
        amihud_illiquidity_21=calc_amihud_illiquidity(close, volume, window=21),
    )


def calc_statistical(ohlcv: pd.DataFrame) -> StatisticalTechnicals:
    """Calculate all statistical indicators.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
    """
    close = ohlcv["adj_close"]
    autocorr = calc_autocorrelation(close)

    return StatisticalTechnicals(
        z_score_50=calc_z_score(close, window=50),
        autocorrelation_lag_1=autocorr[1],
        autocorrelation_lag_5=autocorr[5],
        autocorrelation_lag_10=autocorr[10],
        autocorrelation_lag_21=autocorr[21],
    )


def calc_all_technicals(ohlcv: pd.DataFrame) -> TickerTechnicals:
    """Calculate all technical indicators across all categories.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
              Typically from fetch_bulk_ohlcv_data_for_tickers()[ticker].

    Returns:
        TickerTechnicals containing results from every category.
    """
    return TickerTechnicals(
        trend=calc_trend(ohlcv),
        momentum=calc_momentum(ohlcv),
        volatility=calc_volatility(ohlcv),
        volume=calc_volume(ohlcv),
        statistical=calc_statistical(ohlcv),
    )
