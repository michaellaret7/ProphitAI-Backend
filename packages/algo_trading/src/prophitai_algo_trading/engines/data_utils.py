"""Data utilities shared by all engine types.

Contains data alignment, validation, bar manipulation, and calendar math
used by backtest and live engines.
"""

import math

import pandas as pd

from prophitai_algo_trading.utils.validation import validate_backtest_data

# ================================
# --> Constants
# ================================

# Reason: approximate trading bars per day for each supported interval
_BARS_PER_TRADING_DAY: dict[str, float] = {
    '1min': 390,    # 6.5 hours * 60
    '5min': 78,     # 6.5 hours * 12
    '15min': 26,    # 6.5 hours * 4
    '30min': 13,    # 6.5 hours * 2
    '1hour': 6.5,
    'daily': 1,
}

# ================================
# --> Helper funcs
# ================================


def validate_engine_data(data: dict[str, pd.DataFrame]) -> None:
    """Validate all ticker DataFrames in a multi-ticker data dict.

    Args:
        data: Mapping of ticker → OHLCV DataFrame.

    Raises:
        ValueError: If any DataFrame fails validation.
    """
    for df in data.values():
        validate_backtest_data(df)


def resolve_warmup(
    run_override: int | None,
    init_override: int | None,
    strategy_default: int,
) -> int:
    """Determine the warmup period in bars via 3-tier fallback.

    Args:
        run_override: Explicit override from the run() call.
        init_override: Override set at engine __init__ time.
        strategy_default: Strategy's minimum bars required.

    Returns:
        Number of warmup bars to skip before generating signals.
    """
    if run_override is not None:
        return run_override
    if init_override is not None:
        return init_override
    return strategy_default


def bars_to_calendar_days(bars: int, interval: str, buffer: float = 1.5) -> int:
    """Convert a number of bars + interval to calendar days needed to fetch them.

    Accounts for weekends (5 trading days per 7 calendar days) and applies
    a buffer to handle holidays and partial days.

    Args:
        bars: Number of data points required.
        interval: Bar interval string (e.g. '1min', '15min', 'daily').
        buffer: Safety multiplier to account for holidays/gaps. Defaults to 1.5.

    Returns:
        Minimum calendar days to request, clamped to at least 1.
    """
    bars_per_day = _BARS_PER_TRADING_DAY.get(interval)
    if bars_per_day is None:
        raise ValueError(
            f"Unknown interval '{interval}'. "
            f"Supported: {sorted(_BARS_PER_TRADING_DAY)}"
        )

    trading_days = bars / bars_per_day
    # Reason: 7/5 converts trading days → calendar days
    calendar_days = trading_days * (7 / 5)
    return max(1, math.ceil(calendar_days * buffer))


def align_multi_ticker_data(
    data: dict[str, pd.DataFrame],
) -> tuple[pd.DatetimeIndex, dict[str, pd.DataFrame]]:
    """Align multiple ticker DataFrames to a common datetime index.

    Builds a union datetime index across all tickers, reindexes each DataFrame,
    and adds a ``_has_bar`` boolean column indicating real vs. filled rows.

    Only the ``close`` column is forward-filled (for mark-to-market pricing).
    OHLCV columns are NOT forward-filled to prevent stale data from leaking
    into strategy indicator calculations.

    Args:
        data: Mapping of ticker → OHLCV DataFrame with a DatetimeIndex.

    Returns:
        Tuple of (common DatetimeIndex, dict of reindexed DataFrames with
        ``_has_bar`` column).
    """
    # Reason: set union + single sort is O(N*M + M*log M) vs iterative union O(N * M*log M)
    all_ts: set = set()
    for df in data.values():
        all_ts.update(df.index)
    common_index = pd.DatetimeIndex(sorted(all_ts))

    aligned: dict[str, pd.DataFrame] = {}
    for ticker, df in data.items():
        has_bar = pd.Series(True, index=df.index)
        reindexed = df.reindex(common_index)
        has_bar = has_bar.reindex(common_index, fill_value=False)

        # Reason: forward-fill only close for mark-to-market; stale OHLV is misleading
        reindexed["close"] = reindexed["close"].ffill()
        reindexed["_has_bar"] = has_bar

        aligned[ticker] = reindexed

    return common_index, aligned


def append_bar(data: pd.DataFrame, bar: dict) -> pd.DataFrame:
    """Append or update a bar in a DataFrame.

    Used by event-driven and live engines to incorporate new market data.

    Args:
        data: Existing DataFrame with datetime index.
        bar: Bar dict with 'date' and OHLCV fields.

    Returns:
        DataFrame with the new bar appended or updated.
    """
    new_row = pd.DataFrame([bar])

    if 'date' in new_row.columns:
        new_row['date'] = pd.to_datetime(new_row['date'])
        new_row = new_row.set_index('date')

    if new_row.index[0] in data.index:
        # Reason: only update OHLCV columns, not indicator columns
        for col in new_row.columns:
            data.loc[new_row.index[0], col] = new_row.iloc[0][col]
    else:
        data = pd.concat([data, new_row])

    return data
