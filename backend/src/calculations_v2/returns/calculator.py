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
        normalization: str = "gross",
    ) -> pd.Series:
        """
        Build a DataFrame of aligned returns and apply weights.
        - dropna=True: drop rows with any NaNs (keeps leverage constant).
        - renormalize_each_day=True: renormalize weights over available assets each day.
          normalization:
            - "net"   -> scale to original net exposure (sum of weights)
            - "gross" -> scale to original gross exposure (sum of absolute weights)
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
        gross_target = w.abs().sum()
        if renormalize_each_day:
            eff = mask.mul(w, axis=1)
            row_gross = eff.abs().sum(axis=1)
            if normalization == "gross":
                target = gross_target if gross_target != 0 else 1.0
            else:
                target = net_target if net_target != 0 else 1.0
            adj = eff.div(row_gross.replace(0, np.nan), axis=0) * target
            adj = adj.fillna(0.0)
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


if __name__ == "__main__":
    # Portfolio from JSON
    portfolio = {"MNST": {
        "allocation": 0.05,
        "position": "long"
      },
      "COST": {
        "allocation": 0.05,
        "position": "long"
      },
      "KR": {
        "allocation": 0.05,
        "position": "long"
      },
      "BJ": {
        "allocation": 0.05,
        "position": "long"
      },
      "PG": {
        "allocation": 0.05,
        "position": "long"
      },
      "CL": {
        "allocation": 0.05,
        "position": "long"
      },
      "EPC": {
        "allocation": 0.05,
        "position": "long"
      },
      "HLF": {
        "allocation": 0.05,
        "position": "long"
      },
      "ODD": {
        "allocation": 0.05,
        "position": "long"
      },
      "CCEP": {
        "allocation": 0.05,
        "position": "long"
      },
      "RLX": {
        "allocation": 0.05,
        "position": "long"
      },
      "CHD": {
        "allocation": 0.05,
        "position": "long"
      },
      "MDLZ": {
        "allocation": 0.05,
        "position": "long"
      },
      "PEP": {
        "allocation": 0.05,
        "position": "long"
      },
      "WMT": {
        "allocation": 0.05,
        "position": "long"
      },
      "CASY": {
        "allocation": 0.05,
        "position": "long"
      },
      "SMPL": {
        "allocation": 0.05,
        "position": "long"
      },
      "CELH": {
        "allocation": 0.05,
        "position": "long"
      },
      "FRPT": {
        "allocation": 0.05,
        "position": "long"
      },
      "UVV": {
        "allocation": 0.05,
        "position": "long"
      },
      "UNFI": {
        "allocation": 0.04,
        "position": "short"
      },
      "TGT": {
        "allocation": 0.04,
        "position": "short"
      },
      "PRMB": {
        "allocation": 0.04,
        "position": "short"
      },
      "TAP": {
        "allocation": 0.04,
        "position": "short"
      },
      "STZ": {
        "allocation": 0.04,
        "position": "short"
      },
      "HSY": {
        "allocation": 0.04,
        "position": "short"
      },
      "ADM": {
        "allocation": 0.04,
        "position": "short"
      },
      "ENR": {
        "allocation": 0.04,
        "position": "short"
      },
      "SPB": {
        "allocation": 0.04,
        "position": "short"
      },
      "CLX": {
        "allocation": 0.04,
        "position": "short"
      },
      "DLTR": {
        "allocation": 0.04,
        "position": "short"
      },
      "OLPX": {
        "allocation": 0.04,
        "position": "short"
      },
      "EL": {
        "allocation": 0.04,
        "position": "short"
      },
      "MO": {
        "allocation": 0.04,
        "position": "short"
      },
      "KDP": {
        "allocation": 0.04,
        "position": "short"
      }}
    
    from backend.src.utils.gpt_parser import parse_portfolio_with_gpt
    portfolio = parse_portfolio_with_gpt(portfolio)

    from backend.src.calculations_v2.portfolio.build.builder import CorrelationPortfolioBuilder
    builder = CorrelationPortfolioBuilder()
    portfolio = builder.build_portfolio(portfolio, target_annual_vol=0.17, portfolio_value=1_000_000, leverage=2.0, target_net_exposure=0.20, lookback_days=252, max_position_weight=0.10)
    portfolio = portfolio["final_portfolio"]

    portfolio = parse_portfolio_with_gpt(portfolio)
    print(portfolio)

    # Convert to weights dict (negative for shorts)
    weights = {}
    for ticker, meta in portfolio.items():
        if meta["position"].lower() == "short":
            weights[ticker] = -meta["allocation"]
        else:
            weights[ticker] = meta["allocation"]
    
    # Calculate portfolio metrics
    from backend.src.repositories.price_data import get_price_data_daily, get_dividends_series
    from datetime import datetime, timedelta
    
    # Get tickers
    tickers = list(weights.keys())
    
    # Fetch price data for last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252*4)
    
    # Get price data
    ticker_closes = {}
    ticker_dividends = {}
    
    for ticker in tickers:
        try:
            # Get daily price data
            price_data = get_price_data_daily(
                ticker, 
                start_date, 
                end_date
            )
            
            if price_data is not None and not price_data.empty:
                # Set date as index and get close prices
                price_data['date'] = pd.to_datetime(price_data['date'])
                ticker_closes[ticker] = price_data.set_index('date')['close']
                
                # Get dividends
                divs = get_dividends_series(ticker, start_date, end_date)
                ticker_dividends[ticker] = divs if not divs.empty else pd.Series(0, index=ticker_closes[ticker].index)
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    # Calculate portfolio returns
    if ticker_closes:
        # Price-only return
        ann_price_return = PortfolioReturnsCalculator.annualized_price_return(
            ticker_closes, weights, dropna=False, renormalize_each_day=True
        )
        
        # Total return (with dividends)
        ann_total_return = PortfolioReturnsCalculator.annualized_total_return(
            ticker_closes, ticker_dividends, weights, dropna=False, renormalize_each_day=True
        )
        
        # Daily returns for risk metrics
        ticker_price_returns = {
            t: ReturnsCalculator.daily_price_returns(ticker_closes[t])
            for t in weights if t in ticker_closes
        }
        portfolio_daily = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_price_returns, weights, dropna=False, renormalize_each_day=True
        )
        
        # Calculate volatility
        daily_vol = portfolio_daily.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # Calculate Sharpe (assuming 3% risk-free rate)
        # risk_free = 0.03
        sharpe = (ann_price_return) / annual_vol if annual_vol > 0 else np.nan
        
        print("=== Consumer Staples Portfolio Returns ===")
        print(f"Annualized Price Return: {ann_price_return:.2%}")
        print(f"Annualized Total Return: {ann_total_return:.2%}")
        print(f"Annualized Volatility: {annual_vol:.2%}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Number of positions: {len(weights)}")
        print(f"Long positions: {sum(1 for w in weights.values() if w > 0)}")
        print(f"Short positions: {sum(1 for w in weights.values() if w < 0)}")
        print(f"Net exposure: {sum(weights.values()):.1%}")



