from __future__ import annotations

import numpy as np
import pandas as pd


class ReturnsCalculator:
    """Pure returns utilities for a single ticker time series."""

    @staticmethod
    def daily_price_returns(close: pd.Series) -> pd.Series:
        """Simple daily price returns. Assumes split/dividend-adjusted close for price-only returns."""
        return pd.Series(close).astype(float).pct_change(fill_method=None).dropna()

    @staticmethod
    def total_returns(close: pd.Series, dividends: pd.Series | None = None) -> pd.Series:
        """
        Total simple daily returns with cash dividends (no reinvestment timing):
        r_t = (P_t - P_{t-1})/P_{t-1} + D_t / P_{t-1}
        'dividends' should be per-share cash amounts on ex-dividend dates. Zeros/missing are treated as 0.
        """
        price_ret = ReturnsCalculator.daily_price_returns(close)
        if dividends is None or dividends.empty:
            return price_ret
        c = pd.Series(close).astype(float)
        div = pd.Series(dividends).astype(float)
        div_yield = (div / c.shift(1)).reindex(price_ret.index).fillna(0.0)
        return (price_ret + div_yield).dropna()

    @staticmethod
    def annualized_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
        """CAGR from daily returns over the sample window; returns NaN for empty input."""
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        total_return = float((1.0 + r).prod() - 1.0)
        n = len(r)
        return float((1.0 + total_return) ** (trading_days / n) - 1.0)
    
    @staticmethod
    def annualized_price_return(close: pd.Series, trading_days: int = 252) -> float:
        daily_price_ret = ReturnsCalculator.daily_price_returns(close)
        return ReturnsCalculator.annualized_return(daily_price_ret, trading_days)
    
    @staticmethod
    def annualized_total_return(close: pd.Series, dividends: pd.Series | None = None, trading_days: int = 252) -> float:
        daily_total_ret = ReturnsCalculator.total_returns(close, dividends)
        return ReturnsCalculator.annualized_return(daily_total_ret, trading_days)

    @staticmethod
    def holding_period_return_price_plus_divs_cash(close: pd.Series, dividends: pd.Series | None = None) -> float:
        """
        Cash total (no reinvestment): (P_end - P_start + sum(divs)) / P_start
        """
        c = pd.Series(close).dropna().astype(float)
        if c.empty:
            return np.nan
        start, end = float(c.iloc[0]), float(c.iloc[-1])
        if start <= 0:
            return np.nan
        total_divs = float(pd.Series(dividends).dropna().sum()) if dividends is not None else 0.0
        return float(((end - start) + total_divs) / start)

    @staticmethod
    def holding_period_return_total_reinvested(close: pd.Series, dividends: pd.Series | None = None) -> float:
        """
        Reinvested total return across the period: prod(1 + total_daily_return) - 1
        """
        tr = ReturnsCalculator.total_returns(close, dividends)
        return float((1.0 + tr).prod() - 1.0) if not tr.empty else np.nan

    # Backward-compatibility alias
    @staticmethod
    def holding_period_return(close: pd.Series, dividends: pd.Series | None = None) -> float:
        return ReturnsCalculator.holding_period_return_price_plus_divs_cash(close, dividends)


class PortfolioReturnsCalculator:
    """Portfolio returns from per-ticker daily returns and weights (interpreted as daily-rebalanced)."""

    @staticmethod
    def weighted_daily_returns(
        ticker_returns: dict[str, pd.Series],
        weights: dict[str, float],
        dropna: bool = True,
        renormalize_each_day: bool = False,
    ) -> pd.Series:
        """
        Build a DataFrame of aligned returns and apply weights.
        - dropna=True: drop rows with any NaNs (keeps leverage constant).
        - renormalize_each_day=True: renormalize weights over available assets each day (sums to original net).
        """
        if not ticker_returns or not weights:
            return pd.Series(dtype=float)
        tickers = [t for t in weights if t in ticker_returns]
        if not tickers:
            return pd.Series(dtype=float)
        df_raw = pd.concat({t: pd.Series(ticker_returns[t]).astype(float) for t in tickers}, axis=1)
        if dropna:
            df = df_raw.dropna(how="any")
            mask = df.notna()  # all True after dropna; used only if renormalize_each_day
        else:
            mask = df_raw.notna()
            df = df_raw.fillna(0.0)  # treats missing as 0 return; leverage will vary unless renormalized
        w = pd.Series({t: float(weights[t]) for t in tickers})
        net_target = w.sum()
        if renormalize_each_day:
            eff = mask.mul(w, axis=1)
            row_sums = eff.abs().sum(axis=1)
            adj = eff.div(row_sums.replace(0, np.nan), axis=0) * (net_target if net_target != 0 else 1.0)
            portfolio = (df * adj).sum(axis=1)
        else:
            portfolio = df.dot(w)
        return portfolio
    
    @staticmethod
    def weighted_total_returns(
        ticker_dividends: dict[str, pd.Series],
        ticker_closes: dict[str, pd.Series],
        weights: dict[str, float],
        **kwargs,
    ) -> pd.Series:
        tr = {}
        for t, _w in weights.items():
            if t in ticker_closes:
                divs = ticker_dividends.get(t)
                tr[t] = ReturnsCalculator.total_returns(ticker_closes[t], divs)
        return PortfolioReturnsCalculator.weighted_daily_returns(tr, weights, **kwargs)
    
    @staticmethod
    def annualized_price_return(
        ticker_closes: dict[str, pd.Series],
        weights: dict[str, float],
        trading_days: int = 252,
        **kwargs,
    ) -> float:
        ticker_price_returns = {t: ReturnsCalculator.daily_price_returns(ticker_closes[t])
                                for t in weights if t in ticker_closes}
        portfolio_daily = PortfolioReturnsCalculator.weighted_daily_returns(ticker_price_returns, weights, **kwargs)
        return ReturnsCalculator.annualized_return(portfolio_daily, trading_days)
    
    @staticmethod
    def annualized_total_return(
        ticker_closes: dict[str, pd.Series],
        ticker_dividends: dict[str, pd.Series],
        weights: dict[str, float],
        trading_days: int = 252,
        **kwargs,
    ) -> float:
        portfolio_daily = PortfolioReturnsCalculator.weighted_total_returns(ticker_dividends, ticker_closes, weights, **kwargs)
        return ReturnsCalculator.annualized_return(portfolio_daily, trading_days)



