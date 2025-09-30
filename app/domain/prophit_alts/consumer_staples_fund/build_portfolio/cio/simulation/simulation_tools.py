"""Simulation-aware tool implementations.

This module provides wrapped versions of data-fetching tools that respect the
simulation cutoff date (September 30, 2024). All tools filter data to only return
information that would have been available as of the cutoff date.
"""

import yaml
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from functools import reduce

from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.config import (
    SIMULATION_CUTOFF_DATE,
    is_data_type_available,
    get_unavailable_data_message,
    LOOKBACK_WINDOWS,
)
from app.repositories.ratings_data import (
    get_stock_grades_individual,
    get_stock_grades_summary,
    get_ratings,
)
from app.repositories.price_data import get_dividends_series
from app.repositories.news_data import get_price_target_news
from app.repositories.fundamental_data import get_fundamental_data as _get_fundamental_data


# ==================== Utility Functions ==================== #

def filter_dataframe_by_date(df: pd.DataFrame, cutoff_date: datetime, date_column: str = 'date') -> pd.DataFrame:
    """Filter a DataFrame to only include rows before or on the cutoff date.

    Args:
        df: DataFrame to filter
        cutoff_date: Maximum date to include
        date_column: Name of the date column to filter on

    Returns:
        Filtered DataFrame
    """
    if df is None or df.empty:
        return df

    if date_column not in df.columns:
        return df

    df[date_column] = pd.to_datetime(df[date_column])
    return df[df[date_column] <= cutoff_date]


def filter_series_by_date(series: pd.Series, cutoff_date: datetime) -> pd.Series:
    """Filter a time series to only include dates before or on the cutoff date.

    Args:
        series: Time series to filter (with DatetimeIndex)
        cutoff_date: Maximum date to include

    Returns:
        Filtered series
    """
    if series is None or series.empty:
        return series

    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)

    return series[series.index <= cutoff_date]


def filter_statements_by_date(statements: list, cutoff_date: datetime) -> list:
    """Filter financial statements to only include those dated before or on the cutoff.

    Args:
        statements: List of statement objects with .date attribute
        cutoff_date: Maximum date to include

    Returns:
        Filtered list of statements
    """
    if not statements:
        return statements

    filtered = []
    for stmt in statements:
        if hasattr(stmt, 'date'):
            stmt_date = stmt.date
            if isinstance(stmt_date, str):
                stmt_date = datetime.fromisoformat(stmt_date.replace('Z', '+00:00'))
            elif isinstance(stmt_date, pd.Timestamp):
                stmt_date = stmt_date.to_pydatetime()

            if stmt_date.date() <= cutoff_date.date():
                filtered.append(stmt)
        else:
            # If no date attribute, include it (edge case)
            filtered.append(stmt)

    return filtered


def get_simulation_date_range(data_type: str) -> tuple[datetime, datetime]:
    """Get the appropriate date range for a simulation data request.

    Args:
        data_type: Type of data being requested (news, dividends, etc.)

    Returns:
        Tuple of (start_date, end_date)
    """
    end = SIMULATION_CUTOFF_DATE
    lookback = LOOKBACK_WINDOWS.get(data_type, LOOKBACK_WINDOWS["news"])
    start = end - timedelta(days=lookback)
    return start, end


# ==================== Simulation Tool Implementations ==================== #

def fetch_repository_data_simulation(ticker: str, data_type: str, limit: int | None = None) -> str:
    """Simulation-aware version of fetch_repository_data.

    Filters all data to only return information available as of September 30, 2024.

    Args:
        ticker: Stock ticker symbol
        data_type: Type of data to fetch
        limit: Optional limit on number of items

    Returns:
        YAML string with filtered data or error message
    """
    t = (data_type or "").strip().lower()

    # Check if data type is available in simulation
    if not is_data_type_available(t):
        return yaml.dump({"error": get_unavailable_data_message(t)}, default_flow_style=False)

    start, end = get_simulation_date_range("news")

    # Handle available data types
    if t in ["price_target_news", "pt_news"]:
        data = get_price_target_news(ticker, start=start, end=end, limit=50, ascending=False)
        return yaml.dump(data, default_flow_style=False)

    if t in ["grades_individual", "grades_detail"]:
        data = get_stock_grades_individual(ticker, start=start, end=end)
        return yaml.dump(data, default_flow_style=False)

    if t in ["grades_summary", "grades"]:
        data = get_stock_grades_summary(ticker, start=start, end=end)
        return yaml.dump(data, default_flow_style=False)

    if t == "ratings":
        data = get_ratings(ticker, start=start, end=end)
        return yaml.dump(data, default_flow_style=False)

    if t == "dividends_series":
        div_start, div_end = get_simulation_date_range("dividends")
        s = get_dividends_series(ticker, div_start, div_end)
        s = filter_series_by_date(s, SIMULATION_CUTOFF_DATE)
        items = [{"date": str(idx.date()), "amount": float(val)} for idx, val in s.items()]
        return yaml.dump({"ticker": ticker.upper(), "count": len(items), "items": items}, default_flow_style=False)

    return yaml.dump({"error": f"Unknown or unavailable data_type: {data_type}"}, default_flow_style=False)


def get_fundamental_data_simulation(ticker: str, statement_type: str, quarters_back: int = 2) -> str:
    """Simulation-aware version of get_ticker_fundamental_data.

    Filters fundamental data to only include statements dated before September 30, 2024.

    Args:
        ticker: Stock ticker symbol
        statement_type: Type of statement (income_statement, balance_sheet, etc.)
        quarters_back: Number of quarters to retrieve

    Returns:
        YAML string with filtered fundamental data
    """
    if not isinstance(ticker, str) or not ticker:
        return "Error: Parameter 'ticker' must be a non-empty string."

    valid_types = ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]
    if not isinstance(statement_type, str) or statement_type not in valid_types:
        return f"Error: Parameter 'statement_type' must be one of: {', '.join(valid_types)}."

    if not isinstance(quarters_back, int) or quarters_back < 1:
        return "Error: Parameter 'quarters_back' must be a positive integer."

    # Get fundamentals from repository
    # IMPORTANT: Request more quarters (10x) because the DB may have newer data that will be filtered out
    # For simulation, we need to fetch extra quarters to ensure we get enough data points BEFORE the cutoff
    quarters_to_fetch = min(quarters_back * 10, 40)  # Cap at 40 to avoid excessive data fetching
    result = _get_fundamental_data(ticker, statement_type, quarters_to_fetch)

    # Filter statements by date if data is present
    if "data" in result and isinstance(result["data"], list):
        filtered_data = []
        for item in result["data"]:
            if "date" in item and item["date"]:
                try:
                    item_date = datetime.fromisoformat(str(item["date"]))
                    if item_date <= SIMULATION_CUTOFF_DATE:
                        filtered_data.append(item)
                except Exception:
                    # If date parsing fails, include the item
                    filtered_data.append(item)
            else:
                # If no date, include the item
                filtered_data.append(item)

        result["data"] = filtered_data
        result["quarters_returned"] = len(filtered_data)
        # Update quarters_requested to reflect what user asked for (not inflated amount)
        result["quarters_requested"] = quarters_back

    return yaml.dump(result, default_flow_style=False)


def get_ticker_performance_and_risk_simulation(
    ticker: str,
    *,
    price_data: dict[str, pd.Series] | None = None,
) -> str:
    """Simulation-aware version of get_ticker_performance_and_risk.

    Calculates performance metrics using only data available up to September 30, 2024.

    Args:
        ticker: Stock ticker symbol
        price_data: Optional pre-fetched price data

    Returns:
        YAML string with performance and risk metrics
    """
    # Import here to avoid circular dependencies
    from app.core.calculations.core.data_service import DataService
    from app.core.calculations.returns.calculator import ReturnsCalculator
    from app.core.calculations.performance.calculator import PerformanceCalculator
    from app.core.calculations.risk.calculator import RiskCalculator
    from app.core.calculations.core.config import (
        DEFAULT_TRADING_DAYS,
        DEFAULT_RF_ANNUAL,
        DEFAULT_CONFIDENCE,
    )
    import numpy as np

    # Use simulation cutoff date instead of datetime.now()
    market_ticker = "SPY"
    include_dividends = True
    ds = DataService()
    end_dt = SIMULATION_CUTOFF_DATE
    start_dt = end_dt - timedelta(days=252 * 3)  # 3 years lookback

    def _adjust_for_splits(prices: pd.Series) -> pd.Series:
        """Return split-adjusted close series inferred from large price jumps."""
        if prices is None or prices.empty:
            return prices
        s = prices.astype(float).copy()
        ratio = (s / s.shift(1)).dropna()
        factors = []
        candidate_set = np.array([2, 3, 4, 5, 10], dtype=float)
        for idx, r in ratio.items():
            try:
                if r < 0.7 and r > 0:
                    f = float(candidate_set[np.argmin(np.abs((1.0 / r) - candidate_set))])
                    if abs((1.0 / r) - f) < 0.15:
                        factors.append((idx, f))
                elif r > 1.4:
                    f = float(candidate_set[np.argmin(np.abs(r - candidate_set))])
                    if abs(r - f) < 0.15:
                        factors.append((idx, 1.0 / f))
            except Exception:
                continue
        if not factors:
            return s
        adj = pd.Series(1.0, index=s.index, dtype=float)
        for when, f in factors:
            adj.loc[adj.index < when] *= f
        return s / adj

    # Market series
    try:
        mkt_df = ds.get_price_data(market_ticker, start_dt, end_dt).frame
        mkt_close = mkt_df["close"].astype(float).dropna()
        mkt_close = filter_series_by_date(mkt_close, SIMULATION_CUTOFF_DATE)
        rm = ReturnsCalculator.daily_price_returns(mkt_close)
    except Exception:
        rm = None

    tkr = str(ticker).upper()

    def _round_map(d: Dict[str, Any], ndigits: int = 4) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in d.items():
            try:
                if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                    out[k] = np.nan
                elif isinstance(v, (int, float, np.floating)):
                    out[k] = float(round(float(v), ndigits))
                else:
                    out[k] = v
            except Exception:
                out[k] = v
        return out

    try:
        close = price_data.get(tkr) if price_data else None
        if close is None or close.empty:
            px_df = ds.get_price_data(tkr, start_dt, end_dt).frame
            close = px_df["close"].astype(float).dropna()

        # Filter by simulation cutoff
        close = filter_series_by_date(close, SIMULATION_CUTOFF_DATE)

        if close is not None and not close.empty:
            close = _adjust_for_splits(close)
        if close is None or close.empty:
            return yaml.dump({"error": f"no price data for {tkr}"}, default_flow_style=False)

        if include_dividends:
            try:
                divs = ds.get_dividends(tkr, start_dt, end_dt).series
                divs = filter_series_by_date(divs, SIMULATION_CUTOFF_DATE)
                divs = divs.reindex(close.index).fillna(0.0)
            except Exception:
                divs = None
            r = ReturnsCalculator.total_returns(close, divs)
        else:
            r = ReturnsCalculator.daily_price_returns(close)

        if r.empty:
            return yaml.dump({"error": f"failed to compute returns for {tkr}"}, default_flow_style=False)

        # Risk metrics
        ann_vol = RiskCalculator.annualized_volatility(r)
        risk: Dict[str, Any] = {
            "annualized_volatility": float(ann_vol) if np.isfinite(ann_vol) else np.nan,
            "max_drawdown": float(RiskCalculator.max_drawdown(close)),
            "ulcer_index_price": float(RiskCalculator.ulcer_index(close)),
            "historical_var_1d": float(RiskCalculator.historical_var(r, confidence=DEFAULT_CONFIDENCE)),
            "expected_shortfall_1d": float(RiskCalculator.expected_shortfall(r, confidence=DEFAULT_CONFIDENCE)),
            "parametric_var_1d": float(RiskCalculator.parametric_var(ann_vol, confidence=DEFAULT_CONFIDENCE)),
            "parametric_cvar_1d": float(RiskCalculator.parametric_cvar(ann_vol, confidence=DEFAULT_CONFIDENCE)),
        }

        if rm is not None and not rm.empty:
            beta = RiskCalculator.beta(r, rm)
            up_b, down_b = RiskCalculator.up_down_beta(r, rm)
            risk.update({
                "beta": float(beta) if np.isfinite(beta) else np.nan,
                "up_beta": float(up_b) if np.isfinite(up_b) else np.nan,
                "down_beta": float(down_b) if np.isfinite(down_b) else np.nan,
            })
        else:
            risk.update({"beta": np.nan, "up_beta": np.nan, "down_beta": np.nan})

        risk = _round_map(risk, ndigits=4)

        # Performance metrics
        perf: Dict[str, Any] = {
            "cagr": float(PerformanceCalculator.cagr_from_returns(r)),
            "sharpe": float(PerformanceCalculator.sharpe_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "sortino": float(PerformanceCalculator.sortino_ratio(r, mar_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "calmar_1y": float(PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=1)),
            "omega": float(PerformanceCalculator.omega_ratio_from_annual(r, mar_annual=0.0, periods_per_year=DEFAULT_TRADING_DAYS)),
            "sterling": float(PerformanceCalculator.sterling_ratio_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS)),
            "burke": float(PerformanceCalculator.burke_ratio(r, periods_per_year=DEFAULT_TRADING_DAYS)),
            "martin": float(PerformanceCalculator.martin_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "win_rate": float(PerformanceCalculator.win_rate(r)),
            "profit_factor": float(PerformanceCalculator.profit_factor_from_returns(r)),
            "pain_index": float(PerformanceCalculator.pain_index(r)),
            "tail_ratio": float(PerformanceCalculator.tail_ratio(r)),
            "gain_loss_ratio": float(PerformanceCalculator.gain_loss_ratio(r)),
            "ulcer_index_252": float(PerformanceCalculator.ulcer_index(r, window=DEFAULT_TRADING_DAYS, as_percent=False)),
        }

        if rm is not None and not rm.empty:
            perf.update({
                "treynor": float(PerformanceCalculator.treynor_ratio(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
                "information_ratio": float(PerformanceCalculator.information_ratio(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)),
                "alpha_jensen": float(PerformanceCalculator.alpha_jensen(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
                "tracking_error": float(PerformanceCalculator.tracking_error(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)),
                "appraisal_ratio": float(PerformanceCalculator.appraisal_ratio(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            })
            up_d, down_d = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=None)
            up_a, down_a = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)
            perf.update({
                "up_capture_daily": float(up_d) if up_d is not None and np.isfinite(up_d) else np.nan,
                "down_capture_daily": float(down_d) if down_d is not None and np.isfinite(down_d) else np.nan,
                "up_capture_ann": float(up_a) if up_a is not None and np.isfinite(up_a) else np.nan,
                "down_capture_ann": float(down_a) if down_a is not None and np.isfinite(down_a) else np.nan,
            })
        else:
            perf.update({
                "treynor": np.nan,
                "information_ratio": np.nan,
                "alpha_jensen": np.nan,
                "tracking_error": np.nan,
                "appraisal_ratio": np.nan,
                "up_capture_daily": np.nan,
                "down_capture_daily": np.nan,
                "up_capture_ann": np.nan,
                "down_capture_ann": np.nan,
            })

        perf = _round_map(perf, ndigits=4)

        # Returns summary
        def _trailing_price_return(prices: pd.Series, months: int) -> float:
            if prices is None or prices.empty:
                return np.nan
            end_idx = prices.index[-1]
            start_cut = end_idx - pd.DateOffset(months=months)
            window = prices.loc[prices.index >= start_cut]
            if window.empty:
                return np.nan
            first_px = float(window.iloc[0])
            last_px = float(window.iloc[-1])
            if first_px <= 0:
                return np.nan
            return float(last_px / first_px - 1.0)

        price_return_3y = _trailing_price_return(close, months=36)
        pr_1y = _trailing_price_return(close, months=12)
        pr_6m = _trailing_price_return(close, months=6)
        pr_3m = _trailing_price_return(close, months=3)

        try:
            divs_full = ds.get_dividends(tkr, start_dt, end_dt).series
            divs_full = filter_series_by_date(divs_full, SIMULATION_CUTOFF_DATE)
            divs_full = divs_full.reindex(close.index).fillna(0.0)
        except Exception:
            divs_full = None

        end_idx = close.index[-1]

        # Calculate total returns
        start3 = end_idx - pd.DateOffset(months=36)
        c3 = close.loc[close.index >= start3]
        d3 = divs_full.reindex(c3.index) if divs_full is not None else None
        total_return_3y = float(ReturnsCalculator.holding_period_return_total_reinvested(c3, d3)) if not c3.empty else np.nan

        start1 = end_idx - pd.DateOffset(months=12)
        c1 = close.loc[close.index >= start1]
        d1 = divs_full.reindex(c1.index) if divs_full is not None else None
        total_return_1y = float(ReturnsCalculator.holding_period_return_total_reinvested(c1, d1)) if not c1.empty else np.nan

        start6 = end_idx - pd.DateOffset(months=6)
        c6 = close.loc[close.index >= start6]
        d6 = divs_full.reindex(c6.index) if divs_full is not None else None
        total_return_6m = float(ReturnsCalculator.holding_period_return_total_reinvested(c6, d6)) if not c6.empty else np.nan

        start3m = end_idx - pd.DateOffset(months=3)
        c3m = close.loc[close.index >= start3m]
        d3m = divs_full.reindex(c3m.index) if divs_full is not None else None
        total_return_3m = float(ReturnsCalculator.holding_period_return_total_reinvested(c3m, d3m)) if not c3m.empty else np.nan

        returns: Dict[str, Any] = {
            "price_return_3y": price_return_3y,
            "total_return_3y": total_return_3y,
            "total_return_1y": total_return_1y,
            "total_return_6m": total_return_6m,
            "total_return_3m": total_return_3m,
            "price_return_1y": pr_1y,
            "price_return_6m": pr_6m,
            "price_return_3m": pr_3m,
        }
        returns = _round_map(returns, ndigits=4)

        return yaml.dump({
            "ticker": tkr,
            "market_ticker": market_ticker.upper() if market_ticker else None,
            "num_observations": int(len(r)),
            "simulation_cutoff_date": SIMULATION_CUTOFF_DATE.strftime("%Y-%m-%d"),
            "risk": risk,
            "performance": perf,
            "returns": returns,
        }, default_flow_style=False)

    except Exception as e:
        return yaml.dump({"error": f"failed to compute metrics for {tkr}: {e}"}, default_flow_style=False)


# ============================================================================
# PORTFOLIO RETURNS TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_portfolio_returns_metrics_simulation(portfolio_dict: dict, lookback_days=252) -> str:
    """Simulation-aware version of calculate_portfolio_returns_metrics.

    Uses simulation cutoff date instead of datetime.now() for date range calculation.

    Args:
        portfolio_dict: Portfolio with structure {"TICKER": {"position": "long/short", "allocation": 0.xx}}
        lookback_days: Number of days to look back (default: 252 = 1 year)

    Returns:
        YAML string with portfolio returns metrics
    """
    from app.models.portfolio_models import PortfolioInput
    from app.utils.gpt_parser import canonical_portfolio
    from app.core.calculations.returns.calculator import ReturnsCalculator
    from app.core.calculations.core.data_service import DataService
    import numpy as np

    portfolio_dict = canonical_portfolio(portfolio_dict)

    # Use simulation cutoff date instead of datetime.now()
    end = SIMULATION_CUTOFF_DATE
    start = end - timedelta(days=lookback_days)

    # Get tickers
    tickers = list(portfolio_dict.keys())

    # Fetch price data
    ds = DataService()
    price_data = ds.get_bulk_close_series(tickers, start, end)

    # Filter by simulation cutoff
    price_data = {ticker: filter_series_by_date(series, SIMULATION_CUTOFF_DATE)
                  for ticker, series in price_data.items()}

    # Get dividend data
    dividend_data = {}
    for ticker in tickers:
        try:
            div_data = ds.get_dividends(ticker, start, end)
            dividend_data[ticker] = filter_series_by_date(div_data.series, SIMULATION_CUTOFF_DATE)
        except:
            dividend_data[ticker] = None

    # Convert portfolio to weights (negative for shorts)
    weights = {}
    for ticker, details in portfolio_dict.items():
        if details["position"].lower() == "short":
            weights[ticker] = -abs(details["allocation"])
        else:
            weights[ticker] = abs(details["allocation"])

    # Calculate individual ticker returns (price-only)
    ticker_price_returns = {}
    for ticker in weights:
        if ticker in price_data and not price_data[ticker].empty:
            ticker_price_returns[ticker] = ReturnsCalculator.daily_price_returns(price_data[ticker])

    # Calculate individual ticker returns (total returns with dividends)
    ticker_total_returns = {}
    for ticker in weights:
        if ticker in price_data and not price_data[ticker].empty:
            divs = dividend_data.get(ticker)
            if divs is not None and not divs.empty:
                divs = divs.reindex(price_data[ticker].index).fillna(0.0)
                ticker_total_returns[ticker] = ReturnsCalculator.total_returns(price_data[ticker], divs)
            else:
                ticker_total_returns[ticker] = ReturnsCalculator.daily_price_returns(price_data[ticker])

    # Align returns to common index
    if ticker_price_returns:
        indices = [ret.index for ret in ticker_price_returns.values()]
        common_index = reduce(lambda a, b: a.intersection(b), indices)

        # Calculate portfolio price returns
        portfolio_price_returns = pd.Series(0.0, index=common_index)
        for ticker, weight in weights.items():
            if ticker in ticker_price_returns:
                portfolio_price_returns += weight * ticker_price_returns[ticker].reindex(common_index).fillna(0)

        # Calculate portfolio total returns
        portfolio_total_returns = pd.Series(0.0, index=common_index)
        for ticker, weight in weights.items():
            if ticker in ticker_total_returns:
                portfolio_total_returns += weight * ticker_total_returns[ticker].reindex(common_index).fillna(0)

        # Calculate metrics
        ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
        ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
        ann_volatility = float(portfolio_total_returns.std() * np.sqrt(252))

        # Calculate weekly cumulative returns and convert to rounded dict
        weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
        weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}

        # Calculate cumulative return over period
        total_cumulative = float((1 + portfolio_total_returns).prod() - 1)

        return yaml.dump({
            "ann_price_return": round(ann_price_return, 4),
            "ann_total_return": round(ann_total_return, 4),
            "ann_volatility": round(ann_volatility, 4),
            "weekly_returns": weekly_returns,
            "cumulative_return": round(total_cumulative, 4),
            "simulation_cutoff_date": SIMULATION_CUTOFF_DATE.strftime("%Y-%m-%d"),
        }, default_flow_style=False)
    else:
        return yaml.dump({"error": "No price data available for portfolio tickers"}, default_flow_style=False)


# ============================================================================
# SIMULATION-AWARE UTILITY FUNCTIONS
# ============================================================================

def prepare_portfolio_data_simulation(
    portfolio: Dict,
    lookback_days: int = 252,
    include_dividends: bool = True,
    include_benchmark: Optional[str] = None
):
    """Simulation version of prepare_portfolio_data using cutoff date instead of datetime.now()."""
    from app.core.calculations.core.data_service import DataService
    from app.core.calculations.returns.calculator import ReturnsCalculator

    # Use simulation cutoff date instead of datetime.now()
    end = SIMULATION_CUTOFF_DATE
    start = end - timedelta(days=lookback_days)

    # Get tickers
    tickers = list(portfolio.keys())
    if include_benchmark and include_benchmark not in tickers:
        tickers.append(include_benchmark)

    # Fetch price data
    ds = DataService()
    price_data = ds.get_bulk_close_series(tickers, start, end)

    # Filter by simulation cutoff
    price_data = {ticker: filter_series_by_date(series, SIMULATION_CUTOFF_DATE)
                  for ticker, series in price_data.items()}

    # Get dividend data if requested
    dividend_data = {}
    if include_dividends:
        for ticker in tickers:
            try:
                div_data = ds.get_dividends(ticker, start, end)
                dividend_data[ticker] = filter_series_by_date(div_data.series, SIMULATION_CUTOFF_DATE)
            except:
                dividend_data[ticker] = None

    # Convert portfolio to weights (negative for shorts)
    weights = {}
    for ticker, details in portfolio.items():
        if details["position"].lower() == "short":
            weights[ticker] = -abs(details["allocation"])
        else:
            weights[ticker] = abs(details["allocation"])

    return weights, price_data, dividend_data


def get_portfolio_returns_simulation(
    portfolio: Dict,
    lookback_days: int = 252,
    use_total_returns: bool = True,
    dropna: bool = True,
    renormalize_each_day: bool = False,
    normalization: str = "gross"
):
    """Simulation version of get_portfolio_returns using cutoff date."""
    from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator

    # Get all the data using simulation version
    weights, price_data, dividend_data = prepare_portfolio_data_simulation(
        portfolio,
        lookback_days,
        include_dividends=use_total_returns
    )

    # Calculate individual ticker returns
    ticker_returns = {}
    for ticker in weights:
        if ticker in price_data and not price_data[ticker].empty:
            if use_total_returns and dividend_data.get(ticker) is not None:
                divs = dividend_data[ticker].reindex(price_data[ticker].index).fillna(0.0)
                ticker_returns[ticker] = ReturnsCalculator.total_returns(price_data[ticker], divs)
            else:
                ticker_returns[ticker] = ReturnsCalculator.daily_price_returns(price_data[ticker])

    if not ticker_returns:
        return pd.Series(), weights

    # Calculate portfolio returns - intersect all ticker indices
    from functools import reduce
    indices = [ret.index for ret in ticker_returns.values()]
    common_index = reduce(lambda a, b: a.intersection(b), indices)
    portfolio_returns = pd.Series(0.0, index=common_index)

    for ticker, weight in weights.items():
        if ticker in ticker_returns:
            portfolio_returns += weight * ticker_returns[ticker].reindex(common_index).fillna(0)

    if dropna:
        portfolio_returns = portfolio_returns.dropna()

    return portfolio_returns, weights


def get_benchmark_returns_simulation(
    benchmark: str,
    lookback_days: int = 252,
    use_total_returns: bool = True
):
    """Simulation version of get_benchmark_returns using cutoff date."""
    from app.core.calculations.core.data_service import DataService
    from app.core.calculations.returns.calculator import ReturnsCalculator

    end = SIMULATION_CUTOFF_DATE
    start = end - timedelta(days=lookback_days)

    ds = DataService()
    price_data = ds.get_price_data(benchmark, start, end).frame

    if price_data is None or price_data.empty:
        return pd.Series()

    close = filter_series_by_date(price_data["close"], SIMULATION_CUTOFF_DATE)

    if use_total_returns:
        try:
            div_data = ds.get_dividends(benchmark, start, end)
            divs = filter_series_by_date(div_data.series, SIMULATION_CUTOFF_DATE)
            divs = divs.reindex(close.index).fillna(0.0)
            return ReturnsCalculator.total_returns(close, divs)
        except:
            pass

    return ReturnsCalculator.daily_price_returns(close)


CALCULATE_PORTFOLIO_RETURNS_METRICS_SIMULATION_TOOL = {
    "name": "calculate_portfolio_returns_metrics",
    "description": (
        "Calculate and display simple portfolio return metrics including annualized returns, volatility, and weekly cumulative returns "
        "(SIMULATION MODE - using data up to Sept 30, 2024). "
        "Returns both price-only and total returns (with dividends) for comparison. "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
        "Example: calculate_portfolio_returns_metrics(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}})"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": (
                    "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                    "Complete portfolio with ALL holdings. "
                    "Keys = ticker symbols (e.g., 'AAPL'). "
                    "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                    "Uses 1-year lookback (252 days) ending at simulation cutoff date."
                ),
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {
                                "type": "number",
                                "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                                "minimum": 0,
                                "maximum": 1
                            },
                            "position": {
                                "type": "string",
                                "description": "Must be 'long' or 'short'",
                                "enum": ["long", "short"]
                            }
                        },
                        "required": ["allocation", "position"],
                        "additionalProperties": False
                    }
                },
                "minProperties": 1,
                "additionalProperties": False
            }
        },
        "required": ["portfolio_dict"],
        "additionalProperties": False
    },
    "function": calculate_portfolio_returns_metrics_simulation,
}


# ============================================================================
# CORRELATION MATRIX TOOL (SIMULATION WRAPPER)
# ============================================================================

def correlation_matrix_simulation(portfolio_dict: dict) -> str:
    """Simulation-aware version of correlation_matrix."""
    from app.core.calculations.returns.calculator import ReturnsCalculator
    from app.core.calculations.portfolio.correlation import CorrelationAnalysis
    from app.utils.gpt_parser import canonical_portfolio
    from app.core.calculations.core.helpers import build_returns_df_from_price_map

    if not portfolio_dict:
        return yaml.dump({"correlations": []}, default_flow_style=False)

    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except ValueError:
        return yaml.dump({"correlations": []}, default_flow_style=False)

    # Use simulation version of prepare_portfolio_data
    weights, price_data, dividend_data = prepare_portfolio_data_simulation(
        portfolio=portfolio_dict,
        lookback_days=252,
        include_dividends=False
    )

    if not price_data:
        return yaml.dump({"correlations": []}, default_flow_style=False)

    # Calculate returns
    returns_df = build_returns_df_from_price_map(price_data, drop_rows='none', include_dividends=False)

    if returns_df.empty:
        return yaml.dump({"correlations": []}, default_flow_style=False)

    # Compute correlation matrix
    corr_df = CorrelationAnalysis.correlation_matrix(returns_df)
    if corr_df is None or corr_df.empty:
        return yaml.dump({"correlations": []}, default_flow_style=False)
    corr_df = corr_df.round(3)

    ordered_tickers = [t for t in corr_df.columns if t in corr_df.index]

    # Build records for unique pairs
    records = []
    for i, t1 in enumerate(ordered_tickers):
        for j in range(i + 1, len(ordered_tickers)):
            t2 = ordered_tickers[j]
            value = corr_df.loc[t1, t2]
            try:
                value = float(value)
            except Exception:
                pass
            records.append({
                "pair": f"{t1} | {t2}",
                "corr": value
            })

    return yaml.dump({"correlations": records}, default_flow_style=False)


CORRELATION_MATRIX_SIMULATION_TOOL = {
    "name": "calculate_portfolio_correlation_matrix",
    "description": (
        "Calculate pairwise correlations using 252 trading days of price returns (SIMULATION MODE - data up to Sept 30, 2024). "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
        "Output: {'correlations': [{'pair': 'AAPL | MSFT', 'corr': 0.712}, ...]} (rounded to 3 decimals). "
        "Example: calculate_portfolio_correlation_matrix(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, 'MSFT': {'allocation': 0.125, 'position': 'long'}})"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": "Complete portfolio with ALL holdings.",
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                            "position": {"type": "string", "enum": ["long", "short"]}
                        },
                        "required": ["allocation", "position"],
                        "additionalProperties": False
                    }
                },
                "minProperties": 1,
                "additionalProperties": False
            },
        },
        "required": ["portfolio_dict"],
        "additionalProperties": False
    },
    "function": correlation_matrix_simulation,
}


# ============================================================================
# PORTFOLIO PERFORMANCE TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_portfolio_performance_simulation(
    portfolio_dict: dict,
    lookback_days=756,
    use_total_returns=True,
    rf_annual=0.04,
    benchmark="SPY"
) -> str:
    """Simulation-aware version of calculate_portfolio_performance."""
    from app.core.calculations.returns.calculator import ReturnsCalculator
    from app.core.calculations.risk.calculator import RiskCalculator
    from app.core.calculations.performance.calculator import PerformanceCalculator
    from app.utils.gpt_parser import canonical_portfolio
    import numpy as np

    if not portfolio_dict:
        return yaml.dump({}, default_flow_style=False)

    portfolio_dict = canonical_portfolio(portfolio_dict)

    # Use simulation version of get_portfolio_returns
    portfolio_returns, weights = get_portfolio_returns_simulation(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
        dropna=True,
        normalization="gross"
    )

    if portfolio_returns is None or portfolio_returns.empty:
        return yaml.dump({}, default_flow_style=False)

    # Use simulation version of get_benchmark_returns
    benchmark_returns = get_benchmark_returns_simulation(
        benchmark=benchmark,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns
    )

    # Calculate RF series
    rf_daily = (1.0 + float(rf_annual)) ** (1.0 / 252.0) - 1.0
    rf_series = pd.Series(rf_daily, index=portfolio_returns.index)

    # Core metrics
    ann_return = ReturnsCalculator.annualized_return(portfolio_returns, 252)
    ann_volatility = RiskCalculator.annualized_volatility(portfolio_returns, 252)

    # Risk-adjusted metrics
    sharpe = PerformanceCalculator.sharpe_ratio(portfolio_returns, rf_annual=rf_annual, periods_per_year=252, rf_series=rf_series)
    sortino = PerformanceCalculator.sortino_ratio(portfolio_returns, mar_annual=rf_annual, periods_per_year=252, mar_daily=rf_daily)
    calmar_1y = PerformanceCalculator.calmar_from_returns(portfolio_returns, periods_per_year=252, years=1)

    # Benchmark-relative metrics
    if not benchmark_returns.empty:
        beta = RiskCalculator.beta(portfolio_returns, benchmark_returns)
        alpha = PerformanceCalculator.alpha(portfolio_returns, benchmark_returns, risk_free_daily=rf_daily, trading_days=252)
        alpha_jensen = PerformanceCalculator.alpha_jensen(portfolio_returns, benchmark_returns)
        info_ratio = PerformanceCalculator.information_ratio(portfolio_returns, benchmark_returns)
        treynor = PerformanceCalculator.treynor_ratio(portfolio_returns, benchmark_returns, rf_annual=rf_annual, periods_per_year=252)
        tracking_error = PerformanceCalculator.tracking_error(portfolio_returns, benchmark_returns)
        up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=None)
        up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=252)
    else:
        beta = alpha = alpha_jensen = info_ratio = treynor = tracking_error = float("nan")
        up_cap_daily = down_cap_daily = up_cap_ann = down_cap_ann = float("nan")

    # Advanced metrics
    omega = PerformanceCalculator.omega_ratio_from_annual(portfolio_returns)
    burke = PerformanceCalculator.burke_ratio(portfolio_returns)
    sterling = PerformanceCalculator.sterling_ratio_from_returns(portfolio_returns)
    martin = PerformanceCalculator.martin_ratio(portfolio_returns)

    # Win/loss metrics
    win_rate = PerformanceCalculator.win_rate(portfolio_returns)
    profit_factor = PerformanceCalculator.profit_factor_from_returns(portfolio_returns)

    # Drawdown metrics
    equity = (1.0 + portfolio_returns).cumprod()
    dd = equity / equity.cummax() - 1.0
    max_drawdown = float(dd.min()) if not dd.empty else float("nan")

    # Pain and tail metrics
    pain_index = PerformanceCalculator.pain_index(portfolio_returns)
    tail_ratio = PerformanceCalculator.tail_ratio(portfolio_returns)
    ulcer_index = PerformanceCalculator.ulcer_index(portfolio_returns)

    def _rd(x):
        try:
            return round(float(x), 4)
        except Exception:
            return x

    return yaml.dump({
        "annualized_return": _rd(ann_return),
        "annualized_volatility": _rd(ann_volatility),
        "sharpe": _rd(sharpe),
        "sortino": _rd(sortino),
        "calmar_1y": _rd(calmar_1y),
        "beta": _rd(beta),
        "alpha": _rd(alpha),
        "alpha_jensen": _rd(alpha_jensen),
        "information_ratio": _rd(info_ratio),
        "treynor": _rd(treynor),
        "tracking_error": _rd(tracking_error),
        "up_capture_daily": _rd(up_cap_daily),
        "down_capture_daily": _rd(down_cap_daily),
        "up_capture_annual": _rd(up_cap_ann),
        "down_capture_annual": _rd(down_cap_ann),
        "omega": _rd(omega),
        "burke": _rd(burke),
        "sterling": _rd(sterling),
        "martin": _rd(martin),
        "win_rate": _rd(win_rate),
        "profit_factor": _rd(profit_factor),
        "max_drawdown": _rd(max_drawdown),
        "pain_index": _rd(pain_index),
        "tail_ratio": _rd(tail_ratio),
        "ulcer_index": _rd(ulcer_index),
        "simulation_cutoff_date": SIMULATION_CUTOFF_DATE.strftime("%Y-%m-%d"),
    }, default_flow_style=False)


CALCULATE_PORTFOLIO_PERFORMANCE_SIMULATION_TOOL = {
    "name": "calculate_portfolio_performance",
    "description": (
        "Calculate portfolio performance metrics (SIMULATION MODE - data up to Sept 30, 2024). "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
        "Example: calculate_portfolio_performance(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, ...})"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": "Complete portfolio with ALL holdings. Uses 3-year lookback and SPY benchmark by default.",
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                            "position": {"type": "string", "enum": ["long", "short"]}
                        },
                        "required": ["allocation", "position"],
                        "additionalProperties": False
                    }
                },
                "minProperties": 1,
                "additionalProperties": False
            }
        },
        "required": ["portfolio_dict"],
        "additionalProperties": False
    },
    "function": calculate_portfolio_performance_simulation,
}


# ============================================================================
# PORTFOLIO BETA TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_portfolio_beta_vs_index_simulation(
    portfolio_dict: dict,
    lookback_days: int = 252,
    index_ticker: str = "SPY",
) -> str:
    """Simulation-aware version of calculate_portfolio_beta_vs_index."""
    from app.utils.gpt_parser import canonical_portfolio
    from app.core.calculations.risk.calculator import RiskCalculator
    import numpy as np

    try:
        if not isinstance(portfolio_dict, dict):
            return yaml.dump({"beta": None, "error": "No portfolio_dict provided"}, default_flow_style=False)

        portfolio_dict = canonical_portfolio(portfolio_dict)

        # Use simulation version
        portfolio_returns, _ = get_portfolio_returns_simulation(
            portfolio=portfolio_dict,
            lookback_days=lookback_days + 50,
            use_total_returns=False,
            dropna=True
        )

        if portfolio_returns is None or portfolio_returns.empty:
            return yaml.dump({"beta": None, "error": "No portfolio returns data"}, default_flow_style=False)

        # Use simulation version
        index_returns = get_benchmark_returns_simulation(
            benchmark=index_ticker,
            lookback_days=lookback_days + 50,
            use_total_returns=False
        )

        if index_returns is None or index_returns.empty:
            return yaml.dump({"beta": None, "error": f"No index returns data for {index_ticker}"}, default_flow_style=False)

        beta = RiskCalculator.beta(portfolio_returns, index_returns)

        if pd.isna(beta) or np.isnan(beta):
            return yaml.dump({"beta": None, "error": "Beta calculation resulted in NaN"}, default_flow_style=False)

        return yaml.dump({
            "beta": round(float(beta), 3),
            "simulation_cutoff_date": SIMULATION_CUTOFF_DATE.strftime("%Y-%m-%d")
        }, default_flow_style=False)

    except Exception as e:
        return yaml.dump({"beta": None, "error": str(e)}, default_flow_style=False)


CALCULATE_PORTFOLIO_BETA_VS_INDEX_SIMULATION_TOOL = {
    "name": "calculate_portfolio_beta_vs_index",
    "description": (
        "Calculate CAPM beta for portfolio vs SPY (SIMULATION MODE - data up to Sept 30, 2024). "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
        "Example: calculate_portfolio_beta_vs_index(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...})"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": "Complete portfolio with ALL holdings.",
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                            "position": {"type": "string", "enum": ["long", "short"]}
                        },
                        "required": ["allocation", "position"],
                        "additionalProperties": False
                    }
                },
                "minProperties": 1,
                "additionalProperties": False
            }
        },
        "required": ["portfolio_dict"],
        "additionalProperties": False
    },
    "function": calculate_portfolio_beta_vs_index_simulation,
}