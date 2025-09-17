from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker

def calculate_portfolio_performance(portfolio, lookback_days=252, use_total_returns=True):
    """Simple portfolio performance calculation using gross exposure.
    
    Args:
        portfolio: Dict of holdings with position and allocation
        lookback_days: Number of days to look back
        use_total_returns: If True, include dividends; if False, price-only returns
    """
    
    # Use the new utility function to get portfolio returns
    portfolio_returns, weights = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
        dropna=True,
        normalization="gross"
    )
    
    # Get benchmark returns
    benchmark_returns = get_benchmark_returns(
        benchmark="SPY",
        lookback_days=lookback_days,
        use_total_returns=use_total_returns
    )
    
    # Calculate capture ratios
    up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(
        portfolio_returns, benchmark_returns, periods_per_year=None
    )
    up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(
        portfolio_returns, benchmark_returns, periods_per_year=252
    )
    
    metrics = {
        # Core risk-adjusted metrics
        "sharpe": PerformanceCalculator.sharpe_ratio(portfolio_returns),
        "sortino": PerformanceCalculator.sortino_ratio(portfolio_returns),
        "treynor": PerformanceCalculator.treynor_ratio(portfolio_returns, benchmark_returns),
        "info": PerformanceCalculator.information_ratio(portfolio_returns, benchmark_returns),
        "alpha": PerformanceCalculator.alpha_jensen(portfolio_returns, benchmark_returns),
        
        # Advanced risk-adjusted metrics
        "omega": PerformanceCalculator.omega_ratio(portfolio_returns),
        "sterling": PerformanceCalculator.sterling_ratio_from_returns(portfolio_returns),
        "burke": PerformanceCalculator.burke_ratio(portfolio_returns),
        "martin": PerformanceCalculator.martin_ratio(portfolio_returns),
        
        # Capture ratios
        "up_cap_daily": up_cap_daily,
        "down_cap_daily": down_cap_daily,
        "up_cap_ann": up_cap_ann,
        "down_cap_ann": down_cap_ann,
        
        # Win/loss metrics
        "win_rate": PerformanceCalculator.win_rate(portfolio_returns),
        "pf_ret": PerformanceCalculator.profit_factor_from_returns(portfolio_returns),
        "pf_eq": PerformanceCalculator.profit_factor(portfolio_returns, start_equity=1.0),
        
        # Drawdown and pain metrics
        "pain": PerformanceCalculator.pain_index(portfolio_returns),
        "tail_ratio": PerformanceCalculator.tail_ratio(portfolio_returns, q=5.0),
        "gain_loss": PerformanceCalculator.gain_loss_ratio(portfolio_returns, threshold=0.0, method="mean"),
        "ulcer": PerformanceCalculator.ulcer_index(portfolio_returns, window=None, as_percent=False),
        "ulcer_252pct": PerformanceCalculator.ulcer_index(portfolio_returns, window=252, as_percent=True),
    }
    # Round numeric metrics to 4 decimals, keep non-finite and non-numeric as-is
    metrics = {
        key: (round(value, 4) if isinstance(value, (float, int, np.floating)) and np.isfinite(value) else value)
        for key, value in metrics.items()
    }
    
    return metrics, portfolio_returns

def calculate_portfolio_returns_metrics(portfolio, lookback_days=252):
    """Calculate and display simple portfolio metrics.
    
    Returns:
        dict: Contains annualized returns, volatility, and weekly cumulative returns
    """
    # Get price-only returns
    portfolio_price_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=False,
        dropna=True
    )
    
    # Get total returns
    portfolio_total_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=True,
        dropna=True
    )
    
    # Calculate metrics
    ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
    ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
    ann_volatility = portfolio_total_returns.std() * np.sqrt(252)
    
    # Calculate weekly cumulative returns and convert to rounded dict
    weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
    weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}
    
    # Calculate cumulative return over period
    total_cumulative = (1 + portfolio_total_returns).prod() - 1
    
    return {
        "ann_price_return": round(ann_price_return, 4),
        "ann_total_return": round(ann_total_return, 4),
        "ann_volatility": round(ann_volatility, 4),
        "weekly_returns": weekly_returns,
        "cumulative_return": round(total_cumulative, 4)
    }


def calculate_ticker_performances(portfolio, lookback_days: int = 252, use_total_returns: bool = True, benchmark: str = "SPY") -> pd.DataFrame:
    """Return a DataFrame of performance metrics for each ticker in the portfolio.

    Reuses shared utilities and calculators to fetch data and compute metrics.

    Args:
        portfolio: Dict of holdings with position and allocation
        lookback_days: Number of days to look back
        use_total_returns: If True, include dividends; if False, price-only returns
        benchmark: Benchmark ticker symbol used for relative metrics

    Returns:
        pd.DataFrame where each row corresponds to a ticker and columns are metrics.
    """
    # Fetch inputs via shared utilities
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio=portfolio,
        lookback_days=lookback_days,
        include_dividends=use_total_returns,
        include_benchmark=None,
    )

    # Build per-ticker daily returns
    ticker_returns: dict[str, pd.Series] = {}
    for ticker in weights:
        series = price_data.get(ticker)
        if series is None or series.empty:
            continue
        if use_total_returns:
            divs = dividend_data.get(ticker)
            ticker_returns[ticker] = ReturnsCalculator.total_returns(series, divs)
        else:
            ticker_returns[ticker] = ReturnsCalculator.daily_price_returns(series)

    # Benchmark returns
    benchmark_returns = get_benchmark_returns(
        benchmark=benchmark,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
    )

    rows: list[dict] = []
    for ticker, r in ticker_returns.items():
        try:
            # Core risk-adjusted metrics
            sharpe = PerformanceCalculator.sharpe_ratio(r)
            sortino = PerformanceCalculator.sortino_ratio(r)
            treynor = PerformanceCalculator.treynor_ratio(r, benchmark_returns)
            info = PerformanceCalculator.information_ratio(r, benchmark_returns)
            alpha = PerformanceCalculator.alpha_jensen(r, benchmark_returns)

            # Advanced risk-adjusted metrics
            omega = PerformanceCalculator.omega_ratio_from_annual(r)
            sterling = PerformanceCalculator.sterling_ratio_from_returns(r)
            burke = PerformanceCalculator.burke_ratio(r)
            martin = PerformanceCalculator.martin_ratio(r)

            # Capture ratios
            up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=None)
            up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=252)

            # Win/loss and other diagnostics
            win_rate = PerformanceCalculator.win_rate(r)
            pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
            pf_eq = PerformanceCalculator.profit_factor(r, start_equity=1.0)
            pain = PerformanceCalculator.pain_index(r)
            tail_ratio = PerformanceCalculator.tail_ratio(r, q=5.0)
            gain_loss = PerformanceCalculator.gain_loss_ratio(r, threshold=0.0, method="mean")
            ulcer = PerformanceCalculator.ulcer_index(r, window=None, as_percent=False)
            ulcer_252pct = PerformanceCalculator.ulcer_index(r, window=252, as_percent=True)

            # Additional requested metrics
            equity = (1.0 + r).cumprod()
            max_drawdown = RiskCalculator.max_drawdown(equity)
            ann_total_return = ReturnsCalculator.annualized_return(r, 252)
            ann_volatility = RiskCalculator.annualized_volatility(r, 252)

            row = {
                "ticker": ticker,
                "sharpe": sharpe,
                "sortino": sortino,
                "treynor": treynor,
                "info": info,
                "alpha": alpha,
                "omega": omega,
                "sterling": sterling,
                "burke": burke,
                "martin": martin,
                "up_cap_daily": up_cap_daily,
                "down_cap_daily": down_cap_daily,
                "up_cap_ann": up_cap_ann,
                "down_cap_ann": down_cap_ann,
                "win_rate": win_rate,
                "pf_ret": pf_ret,
                "pf_eq": pf_eq,
                "pain": pain,
                "tail_ratio": tail_ratio,
                "gain_loss": gain_loss,
                "ulcer": ulcer,
                "ulcer_252pct": ulcer_252pct,
                "max_drawdown": max_drawdown,
                "ann_total_return": ann_total_return,
                "ann_volatility": ann_volatility,
            }

            # Round numeric metrics to 4 decimals
            for k, v in list(row.items()):
                if k == "ticker":
                    continue
                if isinstance(v, (float, int, np.floating)) and np.isfinite(v):
                    row[k] = round(float(v), 4)
            rows.append(row)
        except Exception:
            rows.append({"ticker": ticker})

    df = pd.DataFrame(rows)
    # Optional: stable column ordering if data present
    cols = [
        "ticker",
        "sharpe", "sortino", "treynor", "info", "alpha",
        "omega", "sterling", "burke", "martin",
        "up_cap_daily", "down_cap_daily", "up_cap_ann", "down_cap_ann",
        "win_rate", "pf_ret", "pf_eq", "pain", "tail_ratio", "gain_loss",
        "ulcer", "ulcer_252pct",
        "max_drawdown", "ann_total_return", "ann_volatility",
    ]
    if not df.empty:
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
    return df

def calculate_sector_performances(portfolio, lookback_days: int = 252, use_total_returns: bool = True) -> pd.DataFrame:
    return _calculate_group_performances(portfolio, lookback_days, use_total_returns, group_by="sector")

def calculate_industry_performances(portfolio, lookback_days: int = 252, use_total_returns: bool = True) -> pd.DataFrame:
    return _calculate_group_performances(portfolio, lookback_days, use_total_returns, group_by="industry")

def calculate_subindustry_performances(portfolio, lookback_days: int = 252, use_total_returns: bool = True) -> pd.DataFrame:
    return _calculate_group_performances(portfolio, lookback_days, use_total_returns, group_by="sub_industry")

def _get_ticker_group_map(tickers: list[str], group_by: str) -> dict[str, str | None]:
    """Fetch group label per ticker from the database.

    group_by: one of 'sector', 'industry', 'sub_industry'
    """
    field = group_by
    session = MarketSession()
    try:
        rows = (
            session.query(Ticker)
            .filter(Ticker.ticker.in_([t.upper() for t in tickers]))
            .all()
        )
        out: dict[str, str | None] = {}
        for r in rows:
            out[r.ticker] = getattr(r, field, None)
        return out
    finally:
        session.close()


def _calculate_group_performances(portfolio, lookback_days: int, use_total_returns: bool, group_by: str) -> pd.DataFrame:
    """Generic grouping performance calculator.

    Returns a DataFrame with columns: [group_label, ann_total_return, ann_volatility]
    where group_label column name equals group_by.
    """
    # 1) Data and weights
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio=portfolio,
        lookback_days=lookback_days,
        include_dividends=use_total_returns,
        include_benchmark=None,
    )

    tickers = list(weights.keys())
    if not tickers:
        return pd.DataFrame(columns=[group_by, "ann_total_return", "ann_volatility"])

    # 2) Per-ticker return series
    per_ticker_returns: dict[str, pd.Series] = {}
    for t in tickers:
        s = price_data.get(t)
        if s is None or s.empty:
            continue
        if use_total_returns:
            divs = dividend_data.get(t)
            per_ticker_returns[t] = ReturnsCalculator.total_returns(s, divs)
        else:
            per_ticker_returns[t] = ReturnsCalculator.daily_price_returns(s)

    if not per_ticker_returns:
        return pd.DataFrame(columns=[group_by, "ann_total_return", "ann_volatility"])

    # 3) Map tickers to group labels
    ticker_to_group = _get_ticker_group_map(list(per_ticker_returns.keys()), group_by)

    # 4) Build group-level returns using gross-exposure normalization (weights normalized by abs-sum)
    rows: list[dict] = []
    # Group tickers by label
    group_to_tickers: dict[str | None, list[str]] = {}
    for t, lbl in ticker_to_group.items():
        group_to_tickers.setdefault(lbl if lbl is not None else "Unknown", []).append(t)

    for lbl, group_tickers in group_to_tickers.items():
        # Align returns and weights
        r_map = {t: per_ticker_returns[t] for t in group_tickers if t in per_ticker_returns}
        if not r_map:
            continue
        df = pd.concat(r_map, axis=1).dropna(how="any")
        if df.empty:
            continue
        w = pd.Series({t: weights.get(t, 0.0) for t in df.columns}, index=df.columns).astype(float)
        denom = float(np.abs(w).sum())
        if denom > 0:
            w_norm = w / denom
        else:
            # Fallback: equal-weight
            w_norm = pd.Series(1.0 / len(df.columns), index=df.columns)

        grp_returns = (df * w_norm).sum(axis=1)
        ann_ret = ReturnsCalculator.annualized_return(grp_returns, 252)
        ann_vol = RiskCalculator.annualized_volatility(grp_returns, 252)

        row = {
            group_by: lbl,
            "ann_total_return": round(ann_ret, 4) if np.isfinite(ann_ret) else ann_ret,
            "ann_volatility": round(ann_vol, 4) if np.isfinite(ann_vol) else ann_vol,
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    if not out.empty:
        # Stable ordering by label
        out = out[[group_by, "ann_total_return", "ann_volatility"]]
    return out

