from app.core.calculations.portfolio.build.builder import CorrelationPortfolioBuilder
from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.db.core.prophit_alts_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.core.calculations.portfolio.concentration import PortfolioConcentration
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from datetime import datetime, timedelta
from typing import Dict
import pandas as pd
import warnings
import json

from app.core.calculations.core import DataService
from app.core.calculations.core.config import DEFAULT_TRADING_DAYS, DEFAULT_RF_ANNUAL
from app.core.calculations.returns import PortfolioReturnsCalculator, ReturnsCalculator
from app.core.calculations.performance import PerformanceCalculator
from app.core.calculations.risk import RiskCalculator
from app.core.calculations.portfolio.factor_tilt import portfolio_factor_tilts
from app.utils.gpt_parser import parse_portfolio_with_gpt
from app.models.portfolio_models import PortfolioInput
from app.db.core.market_data_models import Ticker

def get_analyst_picks():
    session = ProphitAltsSession()
    initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

    initial_positions_dict = {}
    for position in initial_positions:
        initial_positions_dict[position.ticker_name] = {
            "position": position.position.value,
            "industry": position.industry,
            "conviction": position.conviction,
            "reasoning": position.reasoning
        }

    return initial_positions_dict

def _to_canonical_portfolio(portfolio: PortfolioInput | dict) -> Dict[str, Dict]:
    """Convert any portfolio format to canonical dictionary using GPT parser."""
    # If already in the correct format, return as-is
    if isinstance(portfolio, dict):
        # Check if it's already in canonical format
        if all(isinstance(v, dict) and 'allocation' in v and 'position' in v for v in portfolio.values()):
            # Ensure position is lowercase and allocation is float
            return {
                ticker: {
                    "allocation": float(config['allocation']),
                    "position": config['position'].lower() if isinstance(config['position'], str) else config['position']
                }
                for ticker, config in portfolio.items()
            }
    
    # Use GPT parser for any other format
    return parse_portfolio_with_gpt(portfolio)

def correlation_matrix(portfolio_dict: PortfolioInput | dict, lookback_days: int = 252) -> dict:
    if not portfolio_dict:
        return "You Must provide a portfolio dictionary to calculate the correlation matrix"

    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    tickers = list(portfolio_dict.keys())

    if not tickers:
        return {}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    ds = DataService()
    price_map = ds.get_bulk_close_series(tickers, start_date, end_date)

    if not price_map:
        return {}

    returns_map = {}

    for t, s in price_map.items():
        if s is None or s.empty:
            continue
        try:
            divs = ds.get_dividends(t, start_date, end_date)
            dser = divs.series if divs and divs.series is not None and not divs.series.empty else None
        except Exception:
            dser = None
        tr = ReturnsCalculator.total_returns(s, dser) if dser is not None else ReturnsCalculator.daily_price_returns(s)
        if tr is not None and not tr.empty:
            returns_map[t] = tr
    if not returns_map:
        return {}
    returns_df = pd.DataFrame(returns_map)
    
    corr = CorrelationAnalysis.correlation_matrix(returns_df)
    if corr is None or corr.empty:
        return {}
    # Build raw dict of UNIQUE pairs with correlation > 0.5 (upper triangle, exclude diagonal)
    tickers = list(corr.columns)
    values = corr.values
    pairs: dict[str, float] = {}
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            val = float(values[i, j])
            if val > 0.5:
                key = f"{tickers[i]}|{tickers[j]}"
                pairs[key] = round(val, 3)

    return pairs

def calculate_portfolio_past_performance(
    portfolio_dict: PortfolioInput | dict,
    rf_annual: float = DEFAULT_RF_ANNUAL,
    lookback_years: int = 3,
    benchmark: str = "SPY",
) -> dict:
    """Compute core performance metrics for the portfolio using calculations_v2.

    Returns a dict with metrics rounded to 5 decimals when numeric.
    Uses SPY as the benchmark.
    """
    if not portfolio_dict:
        return "You Must provide a portfolio dictionary to calculate the portfolio past performance"
        
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    # Build signed weights (negative for shorts)
    weights = {}
    for t, cfg in portfolio_dict.items():
        alloc = float(cfg.get("allocation", 0.0) or 0.0)
        pos = (cfg.get("position") or "long").lower()
        weights[t] = -alloc if pos == "short" else alloc

    ds = DataService()
    end = datetime.now()
    start = end - timedelta(days=int(DEFAULT_TRADING_DAYS * max(1, lookback_years)))

    # Fetch prices
    all_tickers = list(weights.keys()) + [benchmark]
    price_map = ds.get_bulk_close_series(all_tickers, start, end)
    if not price_map:
        return {}

    # Per-ticker total returns (prefer dividends-inclusive); fallback to price returns
    ticker_returns = {}
    for t, s in price_map.items():
        if t not in weights or s is None or s.empty:
            continue
        try:
            divs = ds.get_dividends(t, start, end)
            dser = divs.series if divs and divs.series is not None and not divs.series.empty else None
        except Exception:
            dser = None
        tr = ReturnsCalculator.total_returns(s, dser) if dser is not None else ReturnsCalculator.daily_price_returns(s)
        if tr is not None and not tr.empty:
            ticker_returns[t] = tr
    if not ticker_returns:
        return {}

    # Portfolio daily returns (daily rebalanced weights), keep history by renormalizing
    r = PortfolioReturnsCalculator.weighted_daily_returns(
        ticker_returns=ticker_returns,
        weights=weights,
        dropna=False,
        renormalize_each_day=True,
    )
    if r is None or r.empty:
        return {}

    # Benchmark total returns (prefer dividends-inclusive)
    bench_series = price_map.get(benchmark)
    if bench_series is None or bench_series.empty:
        try:
            pd_bench = ds.get_price_data(benchmark, start, end)
            bench_series = pd_bench.frame["close"] if pd_bench and pd_bench.frame is not None and not pd_bench.frame.empty else None
        except Exception:
            bench_series = None
    if bench_series is not None:
        try:
            bdivs = ds.get_dividends(benchmark, start, end)
            bser = bdivs.series if bdivs and bdivs.series is not None and not bdivs.series.empty else None
        except Exception:
            bser = None
        rm = ReturnsCalculator.total_returns(bench_series, bser) if bser is not None else ReturnsCalculator.daily_price_returns(bench_series)
    else:
        rm = pd.Series(dtype=float)

    # Core metrics (use total-return portfolio series; incorporate RF where supported)
    cagr = PerformanceCalculator.cagr_from_returns(r)
    # Build constant daily RF series aligned to r for accuracy
    rf_daily = (1.0 + float(rf_annual)) ** (1.0 / float(DEFAULT_TRADING_DAYS)) - 1.0
    rf_series = pd.Series(rf_daily, index=r.index)
    sharpe = PerformanceCalculator.sharpe_ratio(r, rf_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS, rf_series=rf_series)
    sortino = PerformanceCalculator.sortino_ratio(r, mar_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS, mar_daily=rf_daily)
    # Calmar (3y and 1y)
    calmar = PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=3)
    calmar_1y = PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=1)
    info = PerformanceCalculator.information_ratio(r, rm) if not rm.empty else float("nan")
    alpha = PerformanceCalculator.alpha(r, rm, risk_free_daily=rf_daily, trading_days=DEFAULT_TRADING_DAYS) if not rm.empty else float("nan")
    treynor = PerformanceCalculator.treynor_ratio(r, rm, rf_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS) if not rm.empty else float("nan")
    tracking_error = PerformanceCalculator.tracking_error(r, rm) if not rm.empty else float("nan")
    omega = PerformanceCalculator.omega_ratio_from_annual(r)
    burke = PerformanceCalculator.burke_ratio(r)
    sterling = PerformanceCalculator.sterling_ratio_from_returns(r)
    martin = PerformanceCalculator.martin_ratio(r)
    win_rate = PerformanceCalculator.win_rate(r)
    pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
    tail = PerformanceCalculator.tail_ratio(r)
    ulcer = PerformanceCalculator.ulcer_index(r)
    beta = RiskCalculator.beta(r, rm) if not rm.empty else float("nan")
    # Max drawdown (on portfolio equity)
    equity = (1.0 + r).cumprod()
    dd = equity / equity.cummax() - 1.0
    max_drawdown = float(dd.min()) if not dd.empty else float("nan")

    # Annualized price and total returns (portfolio-level)
    price_closes = {t: price_map[t] for t in weights.keys() if t in price_map}
    # Dividends map (optional; skip ticker on error)
    dividends_map = {}
    for t in weights.keys():
        try:
            divs = ds.get_dividends(t, start, end)
            if divs and divs.series is not None and not divs.series.empty:
                dividends_map[t] = divs.series
        except Exception:
            pass
    annual_price_ret = PortfolioReturnsCalculator.annualized_price_return(price_closes, weights) if price_closes else float("nan")
    annual_total_ret = PortfolioReturnsCalculator.annualized_total_return(price_closes, dividends_map, weights) if price_closes else float("nan")

    # Helper to round floats safely
    def _rd(x):
        try:
            return round(float(x), 5)
        except Exception:
            return x

    return {
        "cagr": _rd(cagr),
        "sharpe": _rd(sharpe),
        "sortino": _rd(sortino),
        "beta": _rd(beta),
        "alpha": _rd(alpha),
        "information_ratio": _rd(info),
        "treynor": _rd(treynor),
        "tracking_error": _rd(tracking_error),
        "omega": _rd(omega),
        "burke": _rd(burke),
        "sterling": _rd(sterling),
        "martin": _rd(martin),
        "max_drawdown": _rd(max_drawdown),
        "win_rate": _rd(win_rate),
        "profit_factor": _rd(pf_ret),
        "tail_ratio": _rd(tail),
        "ulcer_index": _rd(ulcer),
        "annualized_price_return": _rd(annual_price_ret),
        "annualized_total_return": _rd(annual_total_ret),
        "calmar": _rd(calmar),
        "calmar_1y": _rd(calmar_1y),
    }

def exposure_calculator(portfolio_dict: PortfolioInput | dict, exposure_type: str):
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    if exposure_type == "net":
        return PortfolioConcentration(portfolio_dict).net_exposure()
    elif exposure_type == "gross":
        return PortfolioConcentration(portfolio_dict).gross_exposure()
    elif exposure_type == "long":
        return PortfolioConcentration(portfolio_dict).long_exposure()
    elif exposure_type == "short":
        return PortfolioConcentration(portfolio_dict).short_exposure()
    else:
        raise ValueError(f"Invalid exposure type: {exposure_type}")

def industry_concentration(portfolio_dict: PortfolioInput | dict, industry_level: str):
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    if industry_level == "industry":
        res = PortfolioConcentration(portfolio_dict).industry_concentration()
    elif industry_level == "sub_industry":
        res = PortfolioConcentration(portfolio_dict).sub_industry_concentration()
    else:
        raise ValueError(f"Invalid industry level: {industry_level}")
    # Round values to 5 decimals for cleaner display
    return {k: round(float(v), 5) for k, v in res.items()}

#TODO: Add sub-industry concentration

def VaR_calculator(portfolio_dict: PortfolioInput | dict, level: str):
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    if level == "industry":
        res = PortfolioConcentration(portfolio_dict).industry_var()
    elif level == "sub_industry":
        res = PortfolioConcentration(portfolio_dict).sub_industry_var()
    elif level == "portfolio":
        # Single float
        val = PortfolioConcentration(portfolio_dict).portfolio_var()
        return round(float(val), 5) if val is not None else float('nan')
    else:
        raise ValueError(f"Invalid level: {level}")
    # Ensure dict results are rounded to 5 decimals
    return {k: round(float(v), 5) for k, v in res.items()}

def calculate_portfolio_beta_vs_index(
    portfolio_dict: PortfolioInput | Dict[str, Dict], 
    lookback_days: int = 252,
    index_ticker: str = None,
) -> float:
    """
    Calculate CAPM beta for a long/short portfolio vs index.
    
    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use
    
    Returns:
        Portfolio beta vs index
    """
    # Extract weights from portfolio dict, applying sign based on position
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    portfolio_weights = {}
    for ticker, config in portfolio_dict.items():
        allocation = config.get('allocation', 0.0)
        position = config.get('position', 'long')
        # Apply negative sign for short positions
        weight = -allocation if position == 'short' else allocation
        portfolio_weights[ticker] = weight
    
    # Fetch price data
    ds = DataService()
    tickers = list(portfolio_weights.keys()) + [index_ticker]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 50)  # Buffer for returns calc
    
    price_data = ds.get_bulk_close_series(tickers, start_date, end_date)
    
    # Calculate daily returns for each asset
    ticker_returns = {
        ticker: ReturnsCalculator.daily_price_returns(prices)
        for ticker, prices in price_data.items()
        if ticker != index_ticker and prices is not None and not prices.empty
    }
    if not ticker_returns:
        return float('nan')
    
    # Calculate portfolio daily returns
    portfolio_returns = PortfolioReturnsCalculator.weighted_daily_returns(
        ticker_returns=ticker_returns,
        weights=portfolio_weights,
        dropna=True
    )
    if portfolio_returns is None or portfolio_returns.empty:
        return float('nan')
    
    # Get index returns
    spy_series = price_data.get(index_ticker)
    if spy_series is None or spy_series.empty:
        # Fallback fetch for index if not included in bulk result
        spy_pd = ds.get_price_data(index_ticker, start_date, end_date)
        spy_series = spy_pd.frame['close'] if spy_pd and spy_pd.frame is not None and not spy_pd.frame.empty else None
    if spy_series is None or spy_series.empty:
        return float('nan')
    spy_returns = ReturnsCalculator.daily_price_returns(spy_series)
    if spy_returns is None or spy_returns.empty:
        return float('nan')
    
    # Calculate and return beta
    return RiskCalculator.beta(portfolio_returns, spy_returns)

def factor_tilts_for_portfolio(portfolio_dict: PortfolioInput | dict, factors: str) -> dict:
    """Compute and print factor tilts (value/growth/momentum/quality/volatility)."""
    if not portfolio_dict:
        return {}
    portfolio_dict = _to_canonical_portfolio(portfolio_dict)

    # Convert portfolio dict to signed weights expected by calculations_v2
    # Positive for longs, negative for shorts
    weights = {}
    for t, cfg in portfolio_dict.items():
        try:
            alloc = float(cfg.get("allocation", 0.0) or 0.0)
        except Exception:
            alloc = 0.0
        pos = (cfg.get("position") or "long").lower()
        weights[t] = -alloc if pos == "short" else alloc

    # Helper to round numeric values to 4 decimals in the tilt output
    def _round_tilt_output(res: dict) -> dict:
        if not isinstance(res, dict):
            return res
        out = {}
        for k, v in res.items():
            if k == "per_ticker_exposure" and isinstance(v, dict):
                out[k] = {tk: (round(float(tv), 4) if isinstance(tv, (int, float)) else tv) for tk, tv in v.items()}
            elif isinstance(v, (int, float)):
                out[k] = round(float(v), 4)
            else:
                out[k] = v
        return out

    # Keep only summary fields for "all" output
    def _summary(res: dict) -> dict:
        if not isinstance(res, dict):
            return res
        return {k: res.get(k) for k in ["factor", "net_tilt", "long_tilt", "short_tilt"] if k in res}

    if factors == "all":
        return {
            "value": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "value"))),
            "growth": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "growth"))),
            "momentum": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "momentum"))),
            "quality": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "quality"))),
            "volatility": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "volatility")))
        }

    if factors not in ["value", "growth", "momentum", "quality", "volatility", "all"]:
        raise ValueError(f"Invalid factor: {factors}")

    return _round_tilt_output(portfolio_factor_tilts(weights, factors))


def pull_rest_of_ticker_pool():
    session = ProphitAltsSession()
    market_session = MarketSession()
    ticker_pool = session.query(FundInitialPosition).all()

    tickers = []
    for position in ticker_pool:
        tickers.append(position.ticker_name)
    
    ticker_pool_list = []

    rest_of_ticker_pool = market_session.query(Ticker).filter(
        Ticker.ticker.notin_(tickers), 
        Ticker.sector == "equity_sector_consumer_staples",
        Ticker.market_cap > 600_000_000
    ).all()

    for ticker in rest_of_ticker_pool:
        ticker_pool_list.append(ticker.ticker)

    return ticker_pool_list

def build_portfolio(portfolio_dict: any):
    """
    Parse ANY portfolio data into a proper portfolio dict and build optimized portfolio
    
    Args:
        portfolio_data: Any format - string, dict, list, etc.
        Examples:
            - "AAPL 10% long, MSFT 5% short"
            - {"AAPL": 0.1, "MSFT": -0.05}  
            - [("AAPL", 0.1, "long")]
    
    Returns:
        Dict in format: {"TICKER": {"allocation": 0.x, "position": "long/short"}, ...}
        Or error message if build fails
    """
    # Parse any input into portfolio dict format using the canonical converter
    try:
        portfolio_dict = _to_canonical_portfolio(portfolio_dict)
    except Exception as e:
        return f"Error parsing portfolio: {str(e)}"

    # Debug: Check which tickers have price data available
    from datetime import datetime, timedelta
    from app.core.calculations.core import DataService
    
    ds = DataService()
    end = datetime.now()
    start = end - timedelta(days=252)
    requested_tickers = list(portfolio_dict.keys())
    
    # Check price data availability
    price_map = ds.get_bulk_close_series(requested_tickers, start, end)
    missing_tickers = []
    empty_tickers = []
    
    for ticker in requested_tickers:
        if ticker not in price_map:
            missing_tickers.append(ticker)
        elif price_map[ticker] is None or price_map[ticker].empty:
            empty_tickers.append(ticker)
    
    if missing_tickers or empty_tickers:
        error_msg = []
        if missing_tickers:
            error_msg.append(f"Tickers not found in database: {', '.join(missing_tickers)}")
        if empty_tickers:
            error_msg.append(f"Tickers with no price data: {', '.join(empty_tickers)}")
        
        # Return detailed error about which tickers are problematic
        return f"Cannot build portfolio - {'; '.join(error_msg)}. Please use only tickers with available price data."

    built_portfolio = CorrelationPortfolioBuilder().build_portfolio(
        tickers=portfolio_dict,  
        target_annual_vol=0.20,
        portfolio_value=1_000_000,
        leverage=2.0,
        target_net_exposure=0.30,
        lookback_days=252,
        max_position_weight=0.10,
    )
    
    # Check if the build was successful
    if "error" in built_portfolio:
        # Return the error message for debugging
        return f"Portfolio build failed: {built_portfolio['error']}"
    
    if "status" in built_portfolio and built_portfolio["status"] == "success":
        if "final_portfolio" in built_portfolio:
            return built_portfolio["final_portfolio"]
        else:
            return "Error: Build succeeded but final_portfolio not found in result"
    
    # If we get here, something unexpected happened
    return f"Unexpected result structure: {list(built_portfolio.keys())}"

if __name__ == "__main__":
    sample_portfolio = """"arguments": "{\"portfolio_dict\":{\"BJ\":{\"allocation\":0.055,\"position\":\"long\"},\"COST\":{\"allocation\":0.055,\"position\":\"long\"},\"MNST\":{\"allocation\":0.06,\"position\":\"long\"},\"KO\":{\"allocation\":0.045,\"position\":\"long\"},\"CCEP\":{\"allocation\":0.06,\"position\":\"long\"},\"SAM\":{\"allocation\":0.05,\"position\":\"long\"},\"EPC\":{\"allocation\":0.055,\"position\":\"long\"},\"HLF\":{\"allocation\":0.05,\"position\":\"long\"},\"ODD\":{\"allocation\":0.05,\"position\":\"long\"},\"RLX\":{\"allocation\":0.05,\"position\":\"long\"},\"PG\":{\"allocation\":0.05,\"position\":\"long\"},\"CL\":{\"allocation\":0.04,\"position\":\"long\"},\"MDLZ\":{\"allocation\":0.04,\"position\":\"long\"},\"CHD\":{\"allocation\":0.04,\"position\":\"long\"},\"FLO\":{\"allocation\":0.04,\"position\":\"long\"},\"GIS\":{\"allocation\":0.04,\"position\":\"long\"},\"KR\":{\"allocation\":0.05,\"position\":\"long\"},\"PM\":{\"allocation\":0.05,\"position\":\"long\"},\"UNFI\":{\"allocation\":0.06,\"position\":\"short\"},\"TGT\":{\"allocation\":0.055,\"position\":\"short\"},\"PRMB\":{\"allocation\":0.055,\"position\":\"short\"},\"TAP\":{\"allocation\":0.05,\"position\":\"short\"},\"STZ\":{\"allocation\":0.05,\"position\":\"short\"},\"HSY\":{\"allocation\":0.05,\"position\":\"short\"},\"ENR\":{\"allocation\":0.055,\"position\":\"short\"},\"SPB\":{\"allocation\":0.05,\"position\":\"short\"},\"CLX\":{\"allocation\":0.045,\"position\":\"short\"},\"ELF\":{\"allocation\":0.045,\"position\":\"short\"},\"CELH\":{\"allocation\":0.045,\"position\":\"short\"},\"MO\":{\"allocation\":0.045,\"position\":\"short\"}}}"""
    print(build_portfolio(sample_portfolio))