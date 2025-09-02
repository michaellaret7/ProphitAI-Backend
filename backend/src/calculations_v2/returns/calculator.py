from __future__ import annotations

import pandas as pd


class ReturnsCalculator:
    """Pure returns utilities for a single ticker time series."""

    @staticmethod
    def daily_price_returns(close: pd.Series) -> pd.Series:
        return close.pct_change(fill_method=None).dropna()

    @staticmethod
    def total_returns(close: pd.Series, dividends: pd.Series | None = None) -> pd.Series:
        price_ret = ReturnsCalculator.daily_price_returns(close)
        if dividends is None or dividends.empty:
            return price_ret
        div_yield = (dividends / close.shift(1)).reindex(price_ret.index).fillna(0)
        return (price_ret + div_yield).dropna()

    @staticmethod
    def annualized_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return 0.0
        total_return = (1 + daily_returns).prod() - 1
        n = len(daily_returns)
        if n == 0:
            return 0.0
        return (1 + total_return) ** (trading_days / n) - 1

    @staticmethod
    def holding_period_return(close: pd.Series, dividends: pd.Series | None = None) -> float:
        if close.empty:
            return 0.0
        start = close.iloc[0]
        end = close.iloc[-1]
        total_divs = float(dividends.sum()) if dividends is not None else 0.0
        if start == 0:
            return 0.0
        return ((end - start) + total_divs) / start

class PortfolioReturnsCalculator:
    """Portfolio returns utilities from per-ticker daily returns and weights."""

    @staticmethod
    def weighted_daily_returns(ticker_returns: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
        portfolio = pd.Series(dtype=float)
        for t, w in weights.items():
            if t in ticker_returns:
                wr = ticker_returns[t] * w
                portfolio = wr if portfolio.empty else portfolio.add(wr, fill_value=0)
        return portfolio

