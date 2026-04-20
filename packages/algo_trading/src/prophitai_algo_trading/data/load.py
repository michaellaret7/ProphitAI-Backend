"""Canonical data loader for strategy backtests.

Replaces the per-strategy ``load_backtest_data`` functions that each
scaffolded ``wiring.py`` previously hand-rolled. One library-level entry
point guarantees:

1. OHLCV price data is fetched for every ticker.
2. Every declared ``DataRequirement`` is resolved.
3. ``preflight_check`` raises ``DataCoverageError`` if coverage fails —
   the validator catches this and reports ``build_failure``.
4. ``scope="shared"`` requirements with ``broadcast_as`` set are lifted
   from ``df.attrs`` into a per-ticker column on every DataFrame, so
   per-ticker signal models can gate on them without the wiring having
   to remember the broadcast step.

Strategy wiring files should contain a one-liner that calls
``load_backtest_data(...)`` and nothing else. Any logic beyond that is
infrastructure that belongs in this package, not in generated code.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Union

import pandas as pd

from prophitai_algo_trading.data.preflight import preflight_check
from prophitai_algo_trading.data.resolver import build_default_resolver
from prophitai_algo_trading.data.repository.price_data import get_price_data_df

if TYPE_CHECKING:
    from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
    from prophitai_algo_trading.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

DateLike = Union[str, date, datetime]


# ================================
# --> Helper funcs
# ================================


def _fetch_ohlcv(
    tickers: list[str],
    start_date: DateLike,
    end_date: DateLike,
    interval: str,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for each ticker, dropping any that return empty frames."""

    data: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = get_price_data_df(
            symbol=ticker,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

        if not df.empty:
            data[ticker] = df

    return data


def _broadcast_shared_attrs(
    suite: BaseIndicatorSuite,
    data: dict[str, pd.DataFrame],
) -> None:
    """Lift shared attrs into per-ticker columns per their broadcast_as spec.

    Signal models and indicators operate on one ticker's DataFrame at a time
    and can't see ``df.attrs`` from a different ticker. This step copies each
    ``scope="shared"`` requirement that sets ``broadcast_as="col_name"`` into
    every ticker's DataFrame as a column, reindexed to the ticker's date
    index with forward-fill so signal code can do
    ``df["spy_close"] > df["spy_close"].rolling(200).mean()``.
    """

    from prophitai_algo_trading.data.resolver import DataResolver

    resolver = DataResolver()
    requirements = resolver.collect_requirements(suite)

    for req in requirements:
        if req.scope != "shared" or req.broadcast_as is None:
            continue

        column_name = req.broadcast_as

        for ticker, df in data.items():
            blob = df.attrs.get(req.attrs_key)

            if blob is None:
                continue

            # Reason: support Series (commodity, equity_price, economic_indicator)
            # and DataFrame (government_bond_rates, universe_returns). When a
            # DataFrame is shared, broadcast_as refers to the single column the
            # author wants on every per-ticker frame; if it names a missing
            # column we skip silently rather than corrupting the frame.
            if isinstance(blob, pd.Series):
                series = blob
            elif isinstance(blob, pd.DataFrame):
                if column_name in blob.columns:
                    series = blob[column_name]
                elif blob.shape[1] == 1:
                    series = blob.iloc[:, 0]
                else:
                    logger.warning(
                        "broadcast_as=%r: shared DataFrame at attrs_key=%r has "
                        "columns %s — cannot pick one unambiguously; skipping",
                        column_name,
                        req.attrs_key,
                        list(blob.columns),
                    )
                    continue
            else:
                logger.warning(
                    "broadcast_as=%r: shared blob at attrs_key=%r is type %s, "
                    "not Series or DataFrame; skipping",
                    column_name,
                    req.attrs_key,
                    type(blob).__name__,
                )
                continue

            reindexed = series.reindex(df.index, method="ffill")
            df[column_name] = reindexed


# ================================
# --> Public API
# ================================


def load_backtest_data(
    tickers: list[str],
    start_date: DateLike,
    end_date: DateLike,
    *,
    interval: str = "daily",
    indicator_suite: BaseIndicatorSuite | None = None,
    strategy: BaseStrategy | None = None,
    preflight: bool = True,
    universe_min_size: int = 5,
) -> dict[str, pd.DataFrame]:
    """Canonical data loader for every strategy backtest.

    This is the ONLY function a strategy's wiring file needs to call to
    assemble a backtest-ready ``dict[str, pd.DataFrame]``. Handles price
    data, supplementary data resolution, coverage preflight, and shared-
    attr broadcast in one pass.

    Args:
        tickers: Universe to load.
        start_date: ISO date string, ``datetime.date``, or ``datetime.datetime``.
        end_date: ISO date string, ``datetime.date``, or ``datetime.datetime``.
        interval: Bar interval (``"daily"``, ``"hourly"``, ...).
        indicator_suite: The strategy's indicator suite. Exactly one of
            ``indicator_suite`` or ``strategy`` must be provided.
        strategy: The strategy instance. Its ``_indicator_suite`` attribute
            is used when ``indicator_suite`` is not given directly.
        preflight: When ``True`` (default), raise ``DataCoverageError`` if
            any declared DataRequirement fails its ``min_coverage`` gate.
            Set to ``False`` only for exploratory notebooks.
        universe_min_size: Minimum number of tickers that must load OHLCV.

    Returns:
        Dict of ``{ticker: DataFrame}`` with ``df.attrs`` populated and all
        ``broadcast_as`` shared attrs lifted into per-ticker columns.

    Raises:
        DataCoverageError: Coverage preflight failed.
        ValueError: Neither ``indicator_suite`` nor ``strategy`` was provided.
    """

    suite = indicator_suite

    if suite is None and strategy is not None:
        suite = getattr(strategy, "_indicator_suite", None)

    if suite is None:
        raise ValueError(
            "load_backtest_data requires either indicator_suite= or "
            "strategy= so data requirements can be resolved. "
            "Pass strategy=build_strategy(...) from wiring.py."
        )

    data = _fetch_ohlcv(tickers, start_date, end_date, interval)

    if not data:
        # Reason: resolver would no-op on empty data; preflight must still
        # fail loudly. Short-circuit here so the error message names the
        # universe rather than each missing attrs_key.
        if preflight:
            preflight_check(suite, data, universe_min_size=universe_min_size)

        return data

    resolver = build_default_resolver()
    resolver.resolve(suite, data, start_date, end_date)

    if preflight:
        preflight_check(suite, data, universe_min_size=universe_min_size)

    _broadcast_shared_attrs(suite, data)

    return data
