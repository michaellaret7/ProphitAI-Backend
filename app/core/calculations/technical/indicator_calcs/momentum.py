"""Momentum technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .helpers import ema, sma, wilder_ma


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder).

    RSI = 100 - 100 / (1 + RS), where RS = avg_gain / avg_loss (Wilder MA)
    """
    close = df["close"]
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta.clip(upper=0.0))

    avg_gain = wilder_ma(gains, period)
    avg_loss = wilder_ma(losses, period)

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi.name = f"rsi_{period}"
    return rsi


def calculate_stoch(df: pd.DataFrame, k_period: int = 9, d_period: int = 6) -> pd.DataFrame:
    """Stochastic Oscillator (%K and %D).

    %K = 100 * (close - lowest_low) / (highest_high - lowest_low)
    %D = SMA(%K, d_period)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    range_hl = (highest_high - lowest_low).replace(0.0, np.nan)

    k = 100.0 * (close - lowest_low) / range_hl
    d = k.rolling(window=d_period, min_periods=d_period).mean()

    out = pd.DataFrame({
        "stoch_k": k,
        "stoch_d": d,
    })
    return out


def calculate_stoch_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Stochastic RSI (scaled 0..100).

    StochRSI = 100 * (RSI - min(RSI_n)) / (max(RSI_n) - min(RSI_n))
    """
    rsi_series = calculate_rsi(df, period=period)
    min_rsi = rsi_series.rolling(window=period, min_periods=period).min()
    max_rsi = rsi_series.rolling(window=period, min_periods=period).max()
    denom = (max_rsi - min_rsi).replace(0.0, np.nan)
    stoch_rsi = 100.0 * (rsi_series - min_rsi) / denom
    stoch_rsi.name = f"stochrsi_{period}"
    return stoch_rsi


def calculate_macd(
    df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> pd.DataFrame:
    """MACD line, Signal line, and Histogram.

    MACD = EMA(fast) - EMA(slow); Signal = EMA(MACD, signal); Hist = MACD - Signal
    """
    close = df["close"]
    ema_fast = ema(close, fast_period)
    ema_slow = ema(close, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    hist = macd_line - signal_line

    out = pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "hist": hist,
    })
    return out


def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Williams %R (scaled -100..0)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()
    denom = (highest_high - lowest_low).replace(0.0, np.nan)
    willr = -100.0 * (highest_high - close) / denom
    willr.name = f"williams_r_{period}"
    return willr


def calculate_cci(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Commodity Channel Index."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    typical_price = (high + low + close) / 3.0
    sma_tp = sma(typical_price, period)

    # Mean deviation of typical price from its SMA over the lookback
    mean_dev = (
        typical_price.rolling(window=period, min_periods=period)
        .apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=False)
    )

    cci = (typical_price - sma_tp) / (0.015 * mean_dev.replace(0.0, np.nan))
    cci.name = f"cci_{period}"
    return cci


def calculate_roc(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Rate of Change (%)."""
    close = df["close"]
    roc = 100.0 * (close / close.shift(period) - 1.0)
    roc.name = f"roc_{period}"
    return roc


def calculate_ultimate_oscillator(
    df: pd.DataFrame, short: int = 7, medium: int = 14, long: int = 28
) -> pd.Series:
    """Ultimate Oscillator (default 7/14/28 weighting 4:2:1)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    buying_pressure = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    true_range = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat([low, prev_close], axis=1).min(axis=1)

    avg_bp_short = buying_pressure.rolling(window=short, min_periods=short).sum()
    avg_tr_short = true_range.rolling(window=short, min_periods=short).sum()
    avg_bp_med = buying_pressure.rolling(window=medium, min_periods=medium).sum()
    avg_tr_med = true_range.rolling(window=medium, min_periods=medium).sum()
    avg_bp_long = buying_pressure.rolling(window=long, min_periods=long).sum()
    avg_tr_long = true_range.rolling(window=long, min_periods=long).sum()

    uo = 100.0 * (
        4.0 * (avg_bp_short / avg_tr_short.replace(0.0, np.nan))
        + 2.0 * (avg_bp_med / avg_tr_med.replace(0.0, np.nan))
        + 1.0 * (avg_bp_long / avg_tr_long.replace(0.0, np.nan))
    ) / 7.0
    uo.name = "ultimate_oscillator"
    return uo


def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index (MFI) - Volume-weighted RSI.

    Steps:
    1. Typical Price = (High + Low + Close) / 3
    2. Raw Money Flow = Typical Price × Volume
    3. Positive/Negative Money Flow based on typical price direction
    4. Money Flow Ratio = (N-period Positive MF) / (N-period Negative MF)
    5. MFI = 100 - 100 / (1 + Money Flow Ratio)

    Returns values 0-100. Above 80 = overbought, below 20 = oversold.
    """
    if "volume" not in df.columns:
        raise ValueError("MFI requires 'volume' column in dataframe")

    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    # Typical Price
    typical_price = (high + low + close) / 3.0

    # Raw Money Flow
    raw_money_flow = typical_price * volume

    # Determine positive and negative money flow
    tp_diff = typical_price.diff()
    positive_flow = raw_money_flow.where(tp_diff > 0.0, 0.0)
    negative_flow = raw_money_flow.where(tp_diff < 0.0, 0.0)

    # Sum over period
    positive_mf = positive_flow.rolling(window=period, min_periods=period).sum()
    negative_mf = negative_flow.rolling(window=period, min_periods=period).sum()

    # Money Flow Ratio
    mf_ratio = positive_mf / negative_mf.replace(0.0, np.nan)

    # Money Flow Index
    mfi = 100.0 - (100.0 / (1.0 + mf_ratio))
    mfi.name = f"mfi_{period}"
    return mfi


def calculate_td_setup(df: pd.DataFrame) -> pd.DataFrame:
    """TD Setup - DeMark's 9-count setup phase for trend exhaustion.

    Buy Setup: 9 consecutive closes where close[i] < close[i-4]
    Sell Setup: 9 consecutive closes where close[i] > close[i-4]

    Returns:
        DataFrame with columns:
        - buy_setup: Count 1-9 for buy setup bars, 0 otherwise
        - sell_setup: Count 1-9 for sell setup bars, 0 otherwise
        - buy_setup_complete: 1 when buy setup completes (bar 9), 0 otherwise
        - sell_setup_complete: 1 when sell setup completes (bar 9), 0 otherwise
    """
    close = df["close"]
    n = len(df)

    # Compare close with close 4 bars ago
    close_4_ago = close.shift(4)

    # Initialize arrays
    buy_setup = pd.Series(0, index=df.index)
    sell_setup = pd.Series(0, index=df.index)
    buy_setup_complete = pd.Series(0, index=df.index)
    sell_setup_complete = pd.Series(0, index=df.index)

    # Track consecutive counts
    buy_count = 0
    sell_count = 0

    for i in range(4, n):  # Start at 4 since we need 4 bars lookback
        if pd.isna(close_4_ago.iloc[i]):
            continue

        # Check buy setup condition (close < close 4 bars ago)
        if close.iloc[i] < close_4_ago.iloc[i]:
            buy_count += 1
            sell_count = 0  # Reset sell count
            buy_setup.iloc[i] = min(buy_count, 9)
            if buy_count == 9:
                buy_setup_complete.iloc[i] = 1
        # Check sell setup condition (close > close 4 bars ago)
        elif close.iloc[i] > close_4_ago.iloc[i]:
            sell_count += 1
            buy_count = 0  # Reset buy count
            sell_setup.iloc[i] = min(sell_count, 9)
            if sell_count == 9:
                sell_setup_complete.iloc[i] = 1
        else:
            # No clear direction, reset both
            buy_count = 0
            sell_count = 0

    out = pd.DataFrame({
        "buy_setup": buy_setup,
        "sell_setup": sell_setup,
        "buy_setup_complete": buy_setup_complete,
        "sell_setup_complete": sell_setup_complete,
    })
    return out


def calculate_td_countdown(df: pd.DataFrame) -> pd.DataFrame:
    """TD Countdown - DeMark's 13-count countdown phase (non-consecutive).

    Activated after TD Setup completes.
    Buy Countdown: 13 bars where close < low of 2 bars earlier
    Sell Countdown: 13 bars where close > high of 2 bars earlier

    Returns:
        DataFrame with columns:
        - buy_countdown: Count 1-13 for buy countdown bars, 0 otherwise
        - sell_countdown: Count 1-13 for sell countdown bars, 0 otherwise
        - buy_countdown_complete: 1 when buy countdown completes (bar 13), 0 otherwise
        - sell_countdown_complete: 1 when sell countdown completes (bar 13), 0 otherwise
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    # First get setup signals
    setup = calculate_td_setup(df)

    # Initialize arrays
    buy_countdown = pd.Series(0, index=df.index)
    sell_countdown = pd.Series(0, index=df.index)
    buy_countdown_complete = pd.Series(0, index=df.index)
    sell_countdown_complete = pd.Series(0, index=df.index)

    # Track countdown progress
    buy_countdown_active = False
    sell_countdown_active = False
    buy_count = 0
    sell_count = 0
    buy_countdown_values = {}  # Store bar indices for validation
    sell_countdown_values = {}

    for i in range(2, n):  # Start at 2 since we need 2 bars lookback
        # Activate countdown when setup completes
        if setup["buy_setup_complete"].iloc[i] == 1:
            buy_countdown_active = True
            sell_countdown_active = False
            buy_count = 0
            sell_count = 0
            buy_countdown_values = {}
            sell_countdown_values = {}

        if setup["sell_setup_complete"].iloc[i] == 1:
            sell_countdown_active = True
            buy_countdown_active = False
            buy_count = 0
            sell_count = 0
            buy_countdown_values = {}
            sell_countdown_values = {}

        # Buy countdown: close < low of 2 bars earlier
        if buy_countdown_active and buy_count < 13:
            if close.iloc[i] < low.iloc[i - 2]:
                buy_count += 1
                buy_countdown.iloc[i] = buy_count
                buy_countdown_values[buy_count] = i

                # Check completion (bar 13)
                if buy_count == 13:
                    # Additional rule: bar 13 low should be <= bar 8 low for valid signal
                    if 8 in buy_countdown_values:
                        bar_8_idx = buy_countdown_values[8]
                        if low.iloc[i] <= low.iloc[bar_8_idx]:
                            buy_countdown_complete.iloc[i] = 1
                    buy_countdown_active = False  # Reset after completion

        # Sell countdown: close > high of 2 bars earlier
        if sell_countdown_active and sell_count < 13:
            if close.iloc[i] > high.iloc[i - 2]:
                sell_count += 1
                sell_countdown.iloc[i] = sell_count
                sell_countdown_values[sell_count] = i

                # Check completion (bar 13)
                if sell_count == 13:
                    # Additional rule: bar 13 high should be >= bar 8 high for valid signal
                    if 8 in sell_countdown_values:
                        bar_8_idx = sell_countdown_values[8]
                        if high.iloc[i] >= high.iloc[bar_8_idx]:
                            sell_countdown_complete.iloc[i] = 1
                    sell_countdown_active = False  # Reset after completion

    out = pd.DataFrame({
        "buy_countdown": buy_countdown,
        "sell_countdown": sell_countdown,
        "buy_countdown_complete": buy_countdown_complete,
        "sell_countdown_complete": sell_countdown_complete,
    })
    return out


def calculate_td_sequential(df: pd.DataFrame) -> pd.DataFrame:
    """TD Sequential - Complete DeMark Sequential indicator (Setup + Countdown).

    Combines TD Setup and TD Countdown phases to identify precise reversal points.

    Returns:
        DataFrame with all setup and countdown signals:
        - buy_setup, sell_setup: Setup counts (1-9)
        - buy_setup_complete, sell_setup_complete: Setup completion signals
        - buy_countdown, sell_countdown: Countdown counts (1-13)
        - buy_countdown_complete, sell_countdown_complete: Countdown completion signals
        - td_buy_signal: 1 when full buy sequence completes (setup + countdown)
        - td_sell_signal: 1 when full sell sequence completes (setup + countdown)
    """
    setup = calculate_td_setup(df)
    countdown = calculate_td_countdown(df)

    # Combine all signals
    out = pd.concat([setup, countdown], axis=1)

    # Create final buy/sell signals
    out["td_buy_signal"] = (countdown["buy_countdown_complete"] == 1).astype(int)
    out["td_sell_signal"] = (countdown["sell_countdown_complete"] == 1).astype(int)

    return out
