"""Quant metric calculations for the screener cron jobs.

Computes all daily-frequency quant metrics for a single ticker from
already-fetched OHLCV DataFrames (ticker + SPY + optional sector ETF).

All functions are pure — no I/O, no side effects. Inputs are pandas
objects; outputs are dicts of column-name → float (or None).

Note on warnings: the public compute entry points wrap calculation in
a warnings + np.errstate suppression block. NaN/Inf propagation is our
control-flow mechanism — safe_round() converts NaN results to None —
so RuntimeWarnings from numpy/pandas are expected and silenced here.
"""
from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

import numpy as np
import pandas as pd

from prophitai_calculations.performance.ratios import (
    calc_calmar_ratio,
    calc_gain_loss_ratio,
    calc_omega_ratio,
    calc_sharpe_ratio,
    calc_sortino_ratio,
    calc_win_rate,
)
from prophitai_calculations.risk.benchmark import (
    calc_downside_capture,
    calc_rolling_beta,
    calc_upside_capture,
)
from prophitai_calculations.risk.distribution import (
    calc_cvar,
    calc_kurtosis,
    calc_skewness,
    calc_volatility,
)
from prophitai_calculations.risk.drawdown import (
    calc_max_drawdown,
    calc_max_drawdown_duration,
)
from prophitai_calculations.technicals.momentum import (
    calc_adx,
    calc_frog_in_pan,
    calc_momentum_acceleration,
    calc_risk_adj_momentum,
    calc_roc,
    calc_rsi,
    calc_time_series_momentum,
)
from prophitai_calculations.technicals.statistical import (
    calc_hurst_exponent,
    calc_ou_half_life,
)
from prophitai_calculations.technicals.trend import (
    calc_linear_regression,
    calc_sma,
)
from prophitai_calculations.technicals.volatility import (
    calc_atr,
    calc_bollinger_bandwidth,
    calc_close_to_close_volatility,
    calc_donchian_channels,
    calc_yang_zhang_volatility,
)
from prophitai_calculations.technicals.volume import (
    calc_amihud_illiquidity,
    calc_obv,
    calc_roll_spread,
    calc_vwap,
)
from prophitai_jobs.screeners.base import safe_divide, safe_round


# ================================
# --> Helper funcs
# ================================

@contextmanager
def _silence_expected_numerical_warnings() -> Iterator[None]:
    """Suppress RuntimeWarnings + numpy floating-point errors from NaN/Inf ops.

    These fire routinely on sparse/thin tickers (missing OHLCV, zero prices,
    all-NaN rolling windows). NaN results propagate through and are converted
    to None by safe_round(), so the warnings are expected, not bugs.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        with np.errstate(all='ignore'):
            yield


def _last_value(series: pd.Series) -> Optional[float]:
    """Return the last non-NaN float of a series, or None."""
    if series is None or len(series) == 0:
        return None
    clean = series.dropna()
    if len(clean) == 0:
        return None
    return float(clean.iloc[-1])


def _pct_rank_last(series: pd.Series) -> Optional[float]:
    """Percentile rank of the last value within the full series (0-1)."""
    clean = series.dropna()
    if len(clean) < 2:
        return None

    last = clean.iloc[-1]
    rank = (clean <= last).sum() / len(clean)
    return float(rank)


# ================================
# --> Metric groups
# ================================

def _liquidity(close: pd.Series, volume: pd.Series) -> Dict[str, Optional[float]]:
    """Liquidity metrics — all use close * volume."""
    dollar_vol = close * volume

    avg_dv_20d = _last_value(dollar_vol.rolling(window=20, min_periods=20).mean())
    amihud = _last_value(calc_amihud_illiquidity(close, volume, window=252))

    dv_60d = dollar_vol.rolling(window=60, min_periods=60)
    dv_mean = _last_value(dv_60d.mean())
    dv_std = _last_value(dv_60d.std())
    dv_consistency = safe_divide(dv_std, dv_mean) if dv_mean else None

    avg_vol_20d = _last_value(volume.rolling(window=20, min_periods=20).mean())
    today_vol = _last_value(volume)
    rel_vol = safe_divide(today_vol, avg_vol_20d)

    return {
        'avg_dollar_volume_20d': safe_round(avg_dv_20d),
        'amihud_illiquidity': safe_round(amihud, decimals=12),
        'dollar_volume_consistency': safe_round(dv_consistency),
        'relative_volume_20d': safe_round(rel_vol),
    }


def _volatility(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, Optional[float]]:
    """Volatility metrics — ATR, BB width, vol regime, Yang-Zhang, vol ratio."""
    atr_14 = _last_value(calc_atr(high, low, close, window=14))
    last_close = _last_value(close)
    atr_pct = safe_divide(atr_14, last_close) if atr_14 and last_close else None
    bb_width = _last_value(calc_bollinger_bandwidth(close, window=20, num_std=2.0))
    yz_vol = _last_value(calc_yang_zhang_volatility(open_, high, low, close, window=20))

    rolling_vol_20d = calc_close_to_close_volatility(close, window=20, annualize=True)
    vol_regime = _pct_rank_last(rolling_vol_20d.iloc[-252:] if len(rolling_vol_20d) >= 252 else rolling_vol_20d)

    rolling_vol_60d = calc_close_to_close_volatility(close, window=60, annualize=True)
    last_20d = _last_value(rolling_vol_20d)
    last_60d = _last_value(rolling_vol_60d)
    vol_ratio = safe_divide(last_20d, last_60d)

    return {
        'atr_14d': safe_round(atr_14),
        'atr_pct': safe_round(atr_pct),
        'bb_width': safe_round(bb_width),
        'vol_regime_pctile': safe_round(vol_regime),
        'yang_zhang_vol': safe_round(yz_vol),
        'vol_ratio_short_long': safe_round(vol_ratio),
    }


def _momentum_quality(close: pd.Series) -> Dict[str, Optional[float]]:
    """Momentum + quality metrics."""
    mom_12_1 = _last_value(calc_roc(close, window=252, skip_recent=21))
    risk_adj = _last_value(calc_risk_adj_momentum(close))
    rsi = _last_value(calc_rsi(close, window=14))
    tsmom = _last_value(calc_time_series_momentum(close))
    accel = _last_value(calc_momentum_acceleration(close))
    fip = calc_frog_in_pan(close, window=252, skip_recent=21)

    return {
        'momentum_12m_1m_skip': safe_round(mom_12_1),
        'risk_adj_momentum': safe_round(risk_adj),
        'rsi_14d': safe_round(rsi),
        'tsmom': safe_round(tsmom),
        'momentum_acceleration': safe_round(accel),
        'frog_in_pan': safe_round(fip),
    }


def _mean_reversion(close: pd.Series, returns: pd.Series) -> Dict[str, Optional[float]]:
    """Mean-reversion metrics — Hurst, autocorr, OU half-life."""
    hurst = calc_hurst_exponent(close, window=252)

    # Lag-1 autocorrelation over the trailing 252 days
    recent_returns = returns.iloc[-252:] if len(returns) >= 252 else returns
    autocorr = float(recent_returns.autocorr(lag=1)) if len(recent_returns) >= 2 else None
    if autocorr is not None and (np.isnan(autocorr) or np.isinf(autocorr)):
        autocorr = None

    # Apply OU to log-returns (stationary input)
    log_returns_series = np.log(close / close.shift(1)).dropna()
    ou_half_life = calc_ou_half_life(log_returns_series, window=252)

    return {
        'hurst_exponent': safe_round(hurst),
        'autocorrelation_1d': safe_round(autocorr),
        'ou_half_life_logret': safe_round(ou_half_life),
    }


def _trend(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, Optional[float]]:
    """Trend strength — ADX."""
    adx = _last_value(calc_adx(high, low, close, window=14))
    return {'adx_14d': safe_round(adx)}


def _risk_performance(
    returns: pd.Series,
    spy_returns: Optional[pd.Series],
) -> Dict[str, Optional[float]]:
    """Risk, performance, and capture metrics."""
    mdd_1y = calc_max_drawdown(returns, lookback=252) if len(returns) > 0 else None
    mdd_duration = calc_max_drawdown_duration(returns.iloc[-252:]) if len(returns) >= 252 else None
    calmar = calc_calmar_ratio(returns)
    sharpe = calc_sharpe_ratio(returns)
    sortino = calc_sortino_ratio(returns)
    omega = calc_omega_ratio(returns)
    cvar = calc_cvar(returns, confidence=0.95) if len(returns) > 0 else None

    up_cap = None
    down_cap = None
    beta_stability = None
    if spy_returns is not None and len(returns) > 10:
        up_cap = calc_upside_capture(returns, spy_returns)
        down_cap = calc_downside_capture(returns, spy_returns)
        rolling_betas = calc_rolling_beta(returns, spy_returns, window=60)
        if len(rolling_betas) >= 30:
            beta_stability = float(rolling_betas.std())

    return {
        'max_drawdown_1y': safe_round(mdd_1y),
        'max_drawdown_duration_days': safe_round(mdd_duration),
        'calmar_ratio': safe_round(calmar),
        'sharpe_ratio': safe_round(sharpe),
        'sortino_ratio': safe_round(sortino),
        'omega_ratio': safe_round(omega),
        'cvar_95': safe_round(cvar),
        'up_capture_vs_spy': safe_round(up_cap),
        'down_capture_vs_spy': safe_round(down_cap),
        'beta_stability': safe_round(beta_stability),
    }


def _distribution(returns: pd.Series) -> Dict[str, Optional[float]]:
    """Distribution shape metrics."""
    recent = returns.iloc[-252:] if len(returns) >= 252 else returns

    skew = calc_skewness(recent) if len(recent) > 2 else None
    kurt = calc_kurtosis(recent) if len(recent) > 2 else None
    win = calc_win_rate(recent)
    gl = calc_gain_loss_ratio(recent)

    return {
        'return_skewness': safe_round(skew),
        'return_kurtosis': safe_round(kurt),
        'positive_return_ratio': safe_round(win),
        'gain_loss_ratio': safe_round(gl),
    }


def _volume_based(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> Dict[str, Optional[float]]:
    """Volume-based metrics — OBV slope and VWAP distance."""
    obv = calc_obv(close, volume)
    recent_obv = obv.iloc[-60:] if len(obv) >= 60 else obv

    obv_slope_norm = None
    if len(recent_obv) >= 10:
        x = np.arange(len(recent_obv))
        y = recent_obv.to_numpy()
        slope, _ = np.polyfit(x, y, 1)
        avg_vol = float(volume.iloc[-60:].mean()) if len(volume) >= 60 else None
        if avg_vol and avg_vol != 0:
            obv_slope_norm = float(slope) / avg_vol

    vwap = calc_vwap(high, low, close, volume, window=20)
    last_vwap = _last_value(vwap)
    last_close = _last_value(close)
    vwap_dist = (
        (last_close - last_vwap) / last_vwap
        if last_vwap and last_close is not None
        else None
    )

    return {
        'obv_slope_60d': safe_round(obv_slope_norm),
        'vwap_distance_pct': safe_round(vwap_dist),
    }


def _cross_sectional(
    returns: pd.Series,
    close: pd.Series,
    spy_returns: Optional[pd.Series],
    sector_returns: Optional[pd.Series],
    sector_close: Optional[pd.Series],
) -> Dict[str, Optional[float]]:
    """Cross-sectional metrics vs SPY and sector ETF."""
    corr_spy = None
    if spy_returns is not None and len(returns) >= 60:
        aligned = pd.concat([returns.rename('r'), spy_returns.rename('spy')], axis=1).dropna()
        if len(aligned) >= 60:
            corr_series = aligned['r'].rolling(60).corr(aligned['spy'])
            corr_spy = _last_value(corr_series)

    corr_sector = None
    if sector_returns is not None and len(returns) >= 60:
        aligned = pd.concat([returns.rename('r'), sector_returns.rename('sec')], axis=1).dropna()
        if len(aligned) >= 60:
            corr_series = aligned['r'].rolling(60).corr(aligned['sec'])
            corr_sector = _last_value(corr_series)

    # Sector-relative 6-month momentum
    sector_rel_mom = None
    if sector_close is not None and len(close) >= 126 and len(sector_close) >= 126:
        stock_mom_6m = (close.iloc[-1] / close.iloc[-126]) - 1 if close.iloc[-126] else None
        sector_mom_6m = (sector_close.iloc[-1] / sector_close.iloc[-126]) - 1 if sector_close.iloc[-126] else None
        if stock_mom_6m is not None and sector_mom_6m is not None:
            sector_rel_mom = float(stock_mom_6m - sector_mom_6m)

    # Sector-relative volatility
    sector_rel_vol = None
    if sector_returns is not None and len(returns) > 10 and len(sector_returns) > 10:
        stock_vol = calc_volatility(returns, annualize=True)
        sec_vol = calc_volatility(sector_returns, annualize=True)
        if sec_vol and sec_vol != 0:
            sector_rel_vol = float(stock_vol / sec_vol)

    return {
        'corr_to_spy_60d': safe_round(corr_spy),
        'corr_to_sector_60d': safe_round(corr_sector),
        'sector_relative_momentum_6m': safe_round(sector_rel_mom),
        'sector_relative_vol': safe_round(sector_rel_vol),
    }


def _technical_structure(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> Dict[str, Optional[float]]:
    """Technical structure — distance to extremes, MA positioning, Donchian width."""
    last_close = _last_value(close)

    # 52-week high/low distance
    hi_52 = float(high.iloc[-252:].max()) if len(high) >= 252 else None
    lo_52 = float(low.iloc[-252:].min()) if len(low) >= 252 else None
    dist_hi = ((last_close - hi_52) / hi_52) if last_close and hi_52 else None
    dist_lo = ((last_close - lo_52) / lo_52) if last_close and lo_52 else None

    # SMA positioning
    sma200 = _last_value(calc_sma(close, window=200))
    sma50 = _last_value(calc_sma(close, window=50))
    price_vs_sma200 = ((last_close - sma200) / sma200) if last_close and sma200 else None
    price_vs_sma50 = ((last_close - sma50) / sma50) if last_close and sma50 else None

    # Donchian width
    upper, _middle, lower = calc_donchian_channels(high, low, window=20)
    last_upper = _last_value(upper)
    last_lower = _last_value(lower)
    donchian_width = (
        (last_upper - last_lower) / last_close
        if last_upper is not None and last_lower is not None and last_close
        else None
    )

    return {
        'dist_from_52w_high_pct': safe_round(dist_hi),
        'dist_from_52w_low_pct': safe_round(dist_lo),
        'price_vs_sma200_pct': safe_round(price_vs_sma200),
        'price_vs_sma50_pct': safe_round(price_vs_sma50),
        'donchian_width_pct': safe_round(donchian_width),
    }


def _microstructure(close: pd.Series, returns: pd.Series) -> Dict[str, Optional[float]]:
    """Microstructure proxies — zero-return days and Roll spread."""
    recent = returns.iloc[-252:] if len(returns) >= 252 else returns
    zero_pct = float((recent == 0).sum()) / len(recent) if len(recent) > 0 else None
    roll = calc_roll_spread(close, window=252)

    return {
        'zero_return_days_pct': safe_round(zero_pct),
        'roll_spread_estimate': safe_round(roll),
    }


def _return_quality(returns: pd.Series) -> Dict[str, Optional[float]]:
    """Equity-curve smoothness — R² of cumulative return regression."""
    recent = returns.iloc[-252:] if len(returns) >= 252 else returns
    if len(recent) < 30:
        return {'equity_curve_r2': None}

    equity_curve = (1 + recent).cumprod()
    _slope, r_sq = calc_linear_regression(equity_curve, window=len(equity_curve))
    r2_last = _last_value(r_sq)

    return {'equity_curve_r2': safe_round(r2_last)}


# ================================
# --> Public entry points
# ================================

def compute_equity_quant_metrics(
    df: pd.DataFrame,
    spy_df: Optional[pd.DataFrame] = None,
    sector_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Compute all 48 quant metrics for a single equity ticker.

    Args:
        df: OHLCV DataFrame for the ticker (columns: open, high, low, close, adj_close, volume).
        spy_df: Optional OHLCV DataFrame for SPY (benchmark).
        sector_df: Optional OHLCV DataFrame for the sector ETF.

    Returns:
        Dict mapping each screener column name to a value (float or None).
        Safe to merge into the existing screener record dict.
    """
    with _silence_expected_numerical_warnings():
        open_ = df['open']
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']

        returns = close.pct_change(fill_method=None).dropna()
        spy_returns = spy_df['adj_close'].pct_change(fill_method=None).dropna() if spy_df is not None else None
        sector_returns = sector_df['adj_close'].pct_change(fill_method=None).dropna() if sector_df is not None else None
        sector_close = sector_df['close'] if sector_df is not None else None

        metrics: Dict[str, Any] = {}
        metrics.update(_liquidity(close, volume))
        metrics.update(_volatility(open_, high, low, close))
        metrics.update(_momentum_quality(close))
        metrics.update(_mean_reversion(close, returns))
        metrics.update(_trend(high, low, close))
        metrics.update(_risk_performance(returns, spy_returns))
        metrics.update(_distribution(returns))
        metrics.update(_volume_based(high, low, close, volume))
        metrics.update(_cross_sectional(returns, close, spy_returns, sector_returns, sector_close))
        metrics.update(_technical_structure(high, low, close))
        metrics.update(_microstructure(close, returns))
        metrics.update(_return_quality(returns))

        return metrics


def compute_etf_quant_metrics(
    df: pd.DataFrame,
) -> Dict[str, Any]:
    """Compute the 20 quant metrics for a single ETF.

    Args:
        df: OHLCV DataFrame for the ETF.

    Returns:
        Dict mapping each ETF screener column name to a value (float or None).
    """
    with _silence_expected_numerical_warnings():
        open_ = df['open']
        high = df['high']
        low = df['low']
        close = df['close']

        returns = close.pct_change(fill_method=None).dropna()

        metrics: Dict[str, Any] = {}

        # Volatility — ETF schema excludes atr_14d (only atr_pct is kept)
        vol_group = _volatility(open_, high, low, close)
        vol_group.pop('atr_14d', None)
        metrics.update(vol_group)

        # Momentum quality (ETFs skip frog_in_pan and momentum_acceleration)
        metrics['momentum_12m_1m_skip'] = safe_round(_last_value(calc_roc(close, window=252, skip_recent=21)))
        metrics['risk_adj_momentum'] = safe_round(_last_value(calc_risk_adj_momentum(close)))
        metrics['rsi_14d'] = safe_round(_last_value(calc_rsi(close, window=14)))
        metrics['tsmom'] = safe_round(_last_value(calc_time_series_momentum(close)))

        # Mean-reversion (no OU half-life for ETFs)
        metrics['hurst_exponent'] = safe_round(calc_hurst_exponent(close, window=252))
        recent_returns = returns.iloc[-252:] if len(returns) >= 252 else returns
        autocorr = float(recent_returns.autocorr(lag=1)) if len(recent_returns) >= 2 else None
        if autocorr is not None and (np.isnan(autocorr) or np.isinf(autocorr)):
            autocorr = None
        metrics['autocorrelation_1d'] = safe_round(autocorr)

        # Trend
        metrics['adx_14d'] = safe_round(_last_value(calc_adx(high, low, close, window=14)))

        # Risk & performance
        mdd_1y = calc_max_drawdown(returns, lookback=252) if len(returns) > 0 else None
        metrics['max_drawdown_1y'] = safe_round(mdd_1y)
        metrics['sharpe_ratio'] = safe_round(calc_sharpe_ratio(returns))
        metrics['sortino_ratio'] = safe_round(calc_sortino_ratio(returns))
        metrics['cvar_95'] = safe_round(calc_cvar(returns, confidence=0.95)) if len(returns) > 0 else None

        # Distribution
        recent = returns.iloc[-252:] if len(returns) >= 252 else returns
        metrics['return_skewness'] = safe_round(calc_skewness(recent) if len(recent) > 2 else None)
        metrics['return_kurtosis'] = safe_round(calc_kurtosis(recent) if len(recent) > 2 else None)
        metrics['positive_return_ratio'] = safe_round(calc_win_rate(recent))

        # Return quality
        metrics.update(_return_quality(returns))

        return metrics
