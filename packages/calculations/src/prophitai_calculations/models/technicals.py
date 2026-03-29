"""Pydantic models for technical indicator output."""

import pandas as pd
from pydantic import BaseModel, ConfigDict


class TrendTechnicals(BaseModel):
    """Trend indicators — moving averages, regression, and Ichimoku."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sma_20: pd.Series
    sma_50: pd.Series
    sma_200: pd.Series
    ema_12: pd.Series
    ema_26: pd.Series
    ema_50: pd.Series
    ema_200: pd.Series
    linreg_slope_50: pd.Series
    linreg_r_squared_50: pd.Series
    ichimoku_tenkan: pd.Series
    ichimoku_kijun: pd.Series
    ichimoku_senkou_a: pd.Series
    ichimoku_senkou_b: pd.Series
    ichimoku_chikou: pd.Series


class MomentumTechnicals(BaseModel):
    """Momentum indicators — oscillators, trend strength, momentum signals."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    roc_12m: pd.Series
    rsi_14: pd.Series
    macd_line: pd.Series
    macd_signal: pd.Series
    macd_histogram: pd.Series
    adx_14: pd.Series
    risk_adj_momentum: pd.Series
    time_series_momentum: pd.Series
    momentum_acceleration: pd.Series


class VolatilityTechnicals(BaseModel):
    """Volatility indicators — ATR, range-based estimators, Bollinger/Donchian/Keltner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    atr_14: pd.Series
    close_to_close_vol_20: pd.Series
    parkinson_vol_20: pd.Series
    garman_klass_vol_20: pd.Series
    yang_zhang_vol_20: pd.Series
    bollinger_upper: pd.Series
    bollinger_middle: pd.Series
    bollinger_lower: pd.Series
    bollinger_pct_b: pd.Series
    bollinger_bandwidth: pd.Series
    donchian_upper: pd.Series
    donchian_middle: pd.Series
    donchian_lower: pd.Series
    keltner_upper: pd.Series
    keltner_middle: pd.Series
    keltner_lower: pd.Series


class VolumeTechnicals(BaseModel):
    """Volume and liquidity indicators — OBV, VWMA, VWAP, money flow, illiquidity."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    obv: pd.Series
    vwma_20: pd.Series
    vwap_20: pd.Series
    cmf_20: pd.Series
    accumulation_distribution: pd.Series
    mfi_14: pd.Series
    amihud_illiquidity_21: pd.Series


class StatisticalTechnicals(BaseModel):
    """Statistical indicators — z-score, autocorrelation, regime signals."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    z_score_50: pd.Series
    autocorrelation_lag_1: pd.Series
    autocorrelation_lag_5: pd.Series
    autocorrelation_lag_10: pd.Series
    autocorrelation_lag_21: pd.Series


class TickerTechnicals(BaseModel):
    """Top-level container aggregating all technical categories."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trend: TrendTechnicals
    momentum: MomentumTechnicals
    volatility: VolatilityTechnicals
    volume: VolumeTechnicals
    statistical: StatisticalTechnicals
