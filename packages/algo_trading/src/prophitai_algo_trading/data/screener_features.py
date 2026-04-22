"""Shared residual-momentum screener feature computation.

Used by ``ResidualScreenerSnapshotProvider`` (per-ticker monthly snapshots)
and ``UniverseSnapshotPanelProvider`` (shared cross-sectional panel) so
the expensive rolling-regression math runs once per (universe, date-range)
tuple instead of once per provider.

Features computed per ticker from OHLCV + SPY + sector ETFs:
    alpha_vs_spy, alpha_vs_sector, information_ratio,
    beta_vs_sector, adx_14d_snapshot, momentum_12m_1m_skip,
    avg_dollar_volume_20d, price_snapshot.

Constants are used for fields that OHLCV alone cannot produce stably:
    market_cap (50B), beta_stability (0.15), frog_in_pan (0.30).
"""

from __future__ import annotations

import logging
from datetime import date as dt_date
from functools import lru_cache
from typing import Iterable

import numpy as np
import pandas as pd

from prophitai_algo_trading.data.repository.price_data import get_price_data_df

logger = logging.getLogger(__name__)

SECTOR_ETF: dict[str, str] = {
    "Information Technology": "XLK",
    "Technology": "XLK",
    "Health Care": "XLV",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}

_ALPHA_WINDOW = 252
_MARKET_CAP_PLACEHOLDER = 50_000_000_000.0
_BETA_STABILITY_PLACEHOLDER = 0.15
_FROG_IN_PAN_PLACEHOLDER = 0.30


# ================================
# --> Private helpers
# ================================


def _fetch_close(symbol: str, start: dt_date, end: dt_date) -> pd.Series:
    try:
        df = get_price_data_df(
            symbol=symbol, start_date=start, end_date=end, interval="daily"
        )
    except Exception:
        logger.warning("screener_features: failed to fetch %s", symbol, exc_info=True)
        return pd.Series(dtype=float)
    if df.empty or "close" not in df.columns:
        return pd.Series(dtype=float)
    close = df["close"].astype(float).copy()
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close


def _fetch_ohlcv(symbol: str, start: dt_date, end: dt_date) -> pd.DataFrame:
    try:
        df = get_price_data_df(
            symbol=symbol, start_date=start, end_date=end, interval="daily"
        )
    except Exception:
        logger.warning("screener_features: failed to fetch OHLCV for %s", symbol, exc_info=True)
        return pd.DataFrame()
    if df.empty:
        return df
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def _bulk_sectors(tickers: tuple[str, ...]) -> dict[str, str]:
    """Return {ticker: GICS sector label} via the market DB."""
    try:
        from prophitai_data.db.models.market import Ticker as TickerModel
        from prophitai_data.repositories.ticker import get_gics_sector_label
        from prophitai_data.session.decorators import with_session

        @with_session("market")
        def _query(tkrs: list[str], session=None) -> dict[str, str]:
            rows = (
                session.query(TickerModel.ticker, TickerModel.sector)
                .filter(TickerModel.ticker.in_(tkrs))
                .all()
            )
            return {r.ticker: get_gics_sector_label(r.sector or "") for r in rows}

        return _query(list(tickers))
    except Exception:
        logger.warning("screener_features: sector lookup failed", exc_info=True)
        return {}


def _rolling_alpha_beta_ir(
    r: pd.Series, b: pd.Series, window: int
) -> tuple[pd.Series, pd.Series, pd.Series]:
    cov = r.rolling(window).cov(b)
    var = b.rolling(window).var().replace(0.0, np.nan)
    beta = cov / var
    alpha = (r.rolling(window).mean() - beta * b.rolling(window).mean()) * 252.0
    excess = r - b
    ir = (
        excess.rolling(window).mean()
        / excess.rolling(window).std().replace(0.0, np.nan)
    ) * np.sqrt(252.0)
    return alpha, beta, ir


def _wilder_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
) -> pd.Series:
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(
        np.where((up > down) & (up > 0.0), up, 0.0), index=high.index
    )
    minus_dm = pd.Series(
        np.where((down > up) & (down > 0.0), down, 0.0), index=high.index
    )
    prev_close = close.shift()
    tr = pd.Series(
        np.maximum.reduce(
            [
                (high - low).to_numpy(),
                (high - prev_close).abs().to_numpy(),
                (low - prev_close).abs().to_numpy(),
            ]
        ),
        index=high.index,
    )
    alpha = 1.0 / window
    atr = tr.ewm(alpha=alpha, adjust=False).mean().replace(0.0, np.nan)
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=alpha, adjust=False).mean()


def _monthly_first_trading_day_mask(index: pd.DatetimeIndex) -> np.ndarray:
    months = pd.Series(index.to_period("M"), index=index)
    return (months != months.shift(1)).values


def _extract_ratio_ttm(
    ratios: pd.DataFrame | None,
    index: pd.DatetimeIndex,
    column_aliases: Iterable[str],
    filing_lag_days: int = 45,
) -> pd.Series:
    if ratios is None or not isinstance(ratios, pd.DataFrame) or ratios.empty:
        return pd.Series(np.nan, index=index, dtype=float)
    source = next((c for c in column_aliases if c in ratios.columns), None)
    date_col = next(
        (c for c in ("date", "filingDate", "acceptedDate") if c in ratios.columns),
        None,
    )
    if source is None or date_col is None:
        return pd.Series(np.nan, index=index, dtype=float)
    frame = (
        pd.DataFrame(
            {
                "available_from": pd.to_datetime(ratios[date_col], errors="coerce")
                .dt.tz_localize(None)
                .dt.normalize()
                + pd.to_timedelta(filing_lag_days, unit="D"),
                "val": pd.to_numeric(ratios[source], errors="coerce"),
            }
        )
        .dropna()
        .sort_values("available_from")
    )
    if frame.empty:
        return pd.Series(np.nan, index=index, dtype=float)
    left = pd.DataFrame({"t": pd.to_datetime(index).astype("datetime64[ns]")})
    frame["available_from"] = frame["available_from"].astype("datetime64[ns]")
    merged = pd.merge_asof(
        left, frame, left_on="t", right_on="available_from", direction="backward"
    )
    return pd.Series(merged["val"].values, index=index, dtype=float)


def _financial_ratios_by_ticker(
    tickers: tuple[str, ...],
) -> dict[str, pd.DataFrame]:
    try:
        from prophitai_data.repositories.fundamentals import get_bulk_fundamentals
    except Exception:
        logger.warning("screener_features: get_bulk_fundamentals unavailable", exc_info=True)
        return {}
    try:
        bulk = get_bulk_fundamentals(list(tickers))
    except Exception:
        logger.warning("screener_features: bulk fundamentals fetch failed", exc_info=True)
        return {}
    result: dict[str, pd.DataFrame] = {}
    for ticker, fund in bulk.items():
        rows = []
        for row in getattr(fund, "financial_ratios", []) or []:
            if getattr(row, "period", "") == "FY":
                continue
            rows.append(
                {
                    col.name: getattr(row, col.name, None)
                    for col in row.__table__.columns
                    if col.name != "ticker_id"
                }
            )
        if not rows:
            continue
        df = pd.DataFrame(rows)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.sort_values("date").reset_index(drop=True)
        result[ticker] = df
    return result


# ================================
# --> Public API
# ================================


@lru_cache(maxsize=4)
def _cached_features(
    tickers: tuple[str, ...], start_date: dt_date, end_date: dt_date
) -> dict[str, tuple[pd.DataFrame, str]]:
    sectors = _bulk_sectors(tickers)
    sectors_used = {sectors.get(t, "") for t in tickers}
    etf_closes: dict[str, pd.Series] = {
        sec: _fetch_close(SECTOR_ETF[sec], start_date, end_date)
        for sec in sectors_used
        if sec in SECTOR_ETF
    }
    spy = _fetch_close("SPY", start_date, end_date)

    per_ticker: dict[str, tuple[pd.DataFrame, str]] = {}
    for ticker in tickers:
        ohlcv = _fetch_ohlcv(ticker, start_date, end_date)
        if ohlcv.empty:
            continue
        sector = sectors.get(ticker, "")
        etf = etf_closes.get(sector)

        close = ohlcv["close"].astype(float)
        high = ohlcv["high"].astype(float)
        low = ohlcv["low"].astype(float)
        volume = ohlcv["volume"].astype(float)

        r = close.pct_change()
        r_spy = spy.reindex(close.index).pct_change() if not spy.empty else r * np.nan
        r_sec = (
            etf.reindex(close.index).pct_change()
            if etf is not None and not etf.empty
            else r_spy
        )

        alpha_spy, _, ir = _rolling_alpha_beta_ir(r, r_spy, _ALPHA_WINDOW)
        alpha_sec, beta_sec, _ = _rolling_alpha_beta_ir(r, r_sec, _ALPHA_WINDOW)
        adx = _wilder_adx(high, low, close, 14)
        momentum = (close.shift(21) / close.shift(252)) - 1.0
        adv = (close * volume).rolling(20).mean()

        features = pd.DataFrame(
            {
                "alpha_vs_spy": alpha_spy,
                "alpha_vs_sector": alpha_sec,
                "information_ratio": ir,
                "beta_vs_sector": beta_sec,
                "beta_stability": _BETA_STABILITY_PLACEHOLDER,
                "frog_in_pan": _FROG_IN_PAN_PLACEHOLDER,
                "adx_14d_snapshot": adx,
                "momentum_12m_1m_skip": momentum,
                "market_cap": _MARKET_CAP_PLACEHOLDER,
                "avg_dollar_volume_20d": adv,
                "price_snapshot": close,
            },
            index=close.index,
        )
        per_ticker[ticker] = (features, sector)
    return per_ticker


def compute_per_ticker_features(
    tickers: list[str], start_date: dt_date, end_date: dt_date
) -> dict[str, tuple[pd.DataFrame, str]]:
    """Entry point used by providers; memoized on (tickers, start, end)."""
    return _cached_features(tuple(sorted(tickers)), start_date, end_date)


def build_per_ticker_snapshots(
    features_by_ticker: dict[str, tuple[pd.DataFrame, str]],
) -> dict[str, pd.DataFrame]:
    """Resample per-ticker daily features to monthly first-trading-day snapshots."""
    out: dict[str, pd.DataFrame] = {}
    for ticker, (features, _) in features_by_ticker.items():
        mask = _monthly_first_trading_day_mask(features.index)
        monthly = features.loc[mask].copy()
        monthly.insert(0, "snapshot_date", monthly.index)
        monthly.insert(0, "symbol", ticker)
        out[ticker] = monthly.reset_index(drop=True)
    return out


def build_universe_panel(
    features_by_ticker: dict[str, tuple[pd.DataFrame, str]],
    financial_ratios: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Stack per-ticker features into a cross-sectional (date x ticker) panel."""
    financial_ratios = financial_ratios or {}
    rows: list[pd.DataFrame] = []
    for ticker, (features, sector) in features_by_ticker.items():
        ratios = financial_ratios.get(ticker)
        debt = _extract_ratio_ttm(
            ratios, features.index, ("debtRatio", "debtRatioTTM", "debt_ratio_ttm")
        )
        cash = _extract_ratio_ttm(
            ratios, features.index, ("cashRatio", "cashRatioTTM", "cash_ratio_ttm")
        )
        eligible = (
            features["alpha_vs_spy"].notna()
            & features["alpha_vs_sector"].notna()
            & features["information_ratio"].notna()
            & features["beta_vs_sector"].notna()
            & (features["beta_stability"] < 0.25)
            & (features["avg_dollar_volume_20d"] > 10_000_000.0)
            & (features["price_snapshot"] > 5.0)
        ).astype(float)
        rows.append(
            pd.DataFrame(
                {
                    "date": features.index,
                    "symbol": ticker,
                    "sector": sector,
                    "alpha_vs_spy": features["alpha_vs_spy"].values,
                    "alpha_vs_sector": features["alpha_vs_sector"].values,
                    "information_ratio": features["information_ratio"].values,
                    "beta_vs_sector": features["beta_vs_sector"].values,
                    "debt_ratio_ttm": debt.values,
                    "cash_ratio_ttm": cash.values,
                    "eligible_universe_base": eligible.values,
                }
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def fetch_financial_ratios(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Public wrapper so providers that need TTM ratios can reuse the same call."""
    return _financial_ratios_by_ticker(tuple(sorted(tickers)))
