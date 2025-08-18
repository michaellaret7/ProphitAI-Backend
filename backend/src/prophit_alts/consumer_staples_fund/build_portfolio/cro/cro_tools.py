from datetime import datetime, timedelta
import json
from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy.stats import linregress
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker, BalanceSheet, IncomeStatement, CashFlowStatement, FinancialRatio, AnalystEstimate
from backend.src.repositories.price_data import get_price_data_daily, fetch_bulk_price_data_for_tickers
from backend.src.calculations.factor_calculations.growth_factor_calculations import GrowthFactors
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.calculations.factor_calculations.value_factor_calculations import ValueFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.utils.token_count import get_token_count
from backend.src.stress_test.runner import run_stress_test_workflow
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import get_upside_downside_ratios
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *

def get_all_factor_calculations(ticker: str) -> dict:
    """
    Simple function to get all factor calculations for a ticker.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    
    Returns
    -------
    dict
        Dictionary containing all factor calculations:
        - growth_factors
        - momentum_factors
        - quality_factors
        - value_factors
        - volatility_factors
    """
    # Get price data for last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Fetch price data
    price_data = get_price_data_daily(ticker, start_date=start_date, end_date=end_date)
    
    if price_data.empty:
        return {"error": f"No price data found for {ticker}"}
    
    # Extract series
    prices = price_data['close']
    volumes = price_data['volume'] if 'volume' in price_data else None
    
    # Get SPY data for beta calculations
    spy_data = get_price_data_daily('SPY', start_date=start_date, end_date=end_date)
    spy_prices = spy_data['close'] if not spy_data.empty else None
    
    # Calculate all factors
    result = {}
    
    # Growth factors
    growth = GrowthFactors(ticker)
    result['growth_factors'] = growth.calc_all().model_dump()
    
    # Quality factors  
    quality = QualityFactors(ticker)
    result['quality_factors'] = quality.calc_all().model_dump()
    
    # Value factors
    value = ValueFactors(ticker)
    result['value_factors'] = value.calc_all().model_dump()
    
    # Momentum factors
    momentum = MomentumFactors(prices, volumes, spy_prices)
    result['momentum_factors'] = momentum.calc_all().model_dump()
    
    # Volatility factors
    volatility = VolatilityFactors(prices, spy_prices)
    result['volatility_factors'] = volatility.calc_all().model_dump()
    
    return result

def get_ticker_performance_metrics(ticker: str) -> dict:
    """
    Get performance metrics for a ticker.
    """
    performance = TickerPerformanceMetrics(ticker)
    return performance.calc_all().model_dump()

def analyze_portfolio_performance(portfolio_dict: Any, risk_free_rate: float = 0.02) -> dict:
    """
    Analyze portfolio performance over the last ~2 years (≈ 504 trading days).
    
    NOTE: If data is available for less than 2 years, the function will use whatever
    is available. The 'total_return' is the actual return over the holding period,
    while 'annualized_return' extrapolates that to a yearly rate. These can differ
    significantly if the holding period is less than 1 year.

    Parameters
    ----------
    portfolio_dict : dict or str
        Expected format per Dictionary Format Rules:
        - One-line JSON-like mapping using DOUBLE QUOTES, e.g.
          "{"CASY": {"conviction": 0.05, "position": "long"}, "PEP": {"conviction": 0.03, "position": "short"}}"
        - Or a Python dict with the same structure
        - Also supports being wrapped as {"portfolio_dict": { ... }} for backwards compatibility
    risk_free_rate : float
        Annual risk-free rate (e.g., 0.02 for 2%) used for Sharpe/Sortino.

    Returns
    -------
    dict
        {
          'per_ticker_total_returns': {ticker: 'xx.xx%'},
          'portfolio_metrics': {
              'holding_period_days': int,  # actual trading days analyzed
              'holding_period_years': str,  # holding period in years
              'total_return': 'xx.xx%',  # actual return over holding period
              'annualized_return': 'xx.xx%',  # return extrapolated to 1 year
              'annualized_volatility': 'xx.xx%',
              'alpha': float | None,  # annualized alpha (not a percent string)
              'beta': float | None,
              'sharpe_ratio': float | None,
              'sortino_ratio': float | None,
              'max_drawdown': 'xx.xx%'
          }
        }
    """
    # Normalize/parse input to mapping: ticker -> {conviction: float, position: str}
    portfolio: Dict[str, Any]
    if isinstance(portfolio_dict, str):
        try:
            parsed = json.loads(portfolio_dict)
        except Exception:
            raise ValueError("Invalid portfolio_dict string. Must be valid JSON with double quotes.")
        portfolio = parsed.get('portfolio_dict', parsed)
        if isinstance(portfolio, str):
            portfolio = json.loads(portfolio)
    elif isinstance(portfolio_dict, dict):
        portfolio = portfolio_dict.get('portfolio_dict', portfolio_dict)
        if isinstance(portfolio, str):
            portfolio = json.loads(portfolio)
    else:
        raise ValueError("portfolio_dict must be a dict or JSON string per Dictionary Format Rules")

    if not isinstance(portfolio, dict) or not portfolio:
        raise ValueError("Parsed portfolio must be a non-empty dict of tickers")

    # Period: aim for >= 504 trading days; request a buffer in calendar days then trim
    end_date = datetime.now().date()
    start_date = (datetime.now() - timedelta(days=252*2 + 60)).date()  # buffer to ensure we get 504 trading days
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Build list of tickers and include benchmark SPY for alpha/beta
    tickers = sorted({t.upper() for t in portfolio.keys()})
    all_tickers = tickers + ['SPY'] if 'SPY' not in tickers else tickers

    # Fetch adjusted close series for all tickers in parallel
    prices_map = fetch_bulk_price_data_for_tickers(all_tickers, start_date_str, end_date_str, frequency='daily')

    # Construct price DataFrame and isolate SPY
    spy_close = None
    if 'SPY' in prices_map:
        spy_close = prices_map.pop('SPY')

    if not prices_map:
        raise ValueError("No price data available for provided tickers")

    prices_df = pd.DataFrame(prices_map)
    if prices_df.empty:
        raise ValueError("Price DataFrame is empty after fetch")

    # Compute daily returns; align across tickers and trim to last 504 observations
    returns_df = prices_df.pct_change().dropna(how='any')
    if len(returns_df) > 252*2:
        returns_df = returns_df.tail(252*2)

    # Per-ticker total returns
    per_ticker_total_returns = (1.0 + returns_df).prod() - 1.0
    per_ticker_total_returns_pct = {
        ticker: f"{ret * 100.0:.2f}%" for ticker, ret in per_ticker_total_returns.sort_values(ascending=False).items()
    }

    # Build signed weights from conviction and position
    weights = {}
    for ticker, details in portfolio.items():
        if ticker.upper() in returns_df.columns:
            conviction = float(details.get('conviction', 0.0))
            position = str(details.get('position', 'long')).lower()
            weight = -conviction if position == 'short' else conviction
            weights[ticker.upper()] = weight

    if not weights:
        raise ValueError("No overlapping tickers between portfolio and returns data")

    weights_series = pd.Series(weights).reindex(returns_df.columns).fillna(0.0)

    # Daily portfolio returns (weighted sum of component returns)
    portfolio_returns = (returns_df * weights_series).sum(axis=1)
    # Name series for consistent column names on concat
    portfolio_returns.name = 'portfolio'

    # Portfolio total return and annualized metrics
    if portfolio_returns.empty:
        raise ValueError("Portfolio returns series is empty")

    holding_total_return = (1.0 + portfolio_returns).prod() - 1.0
    num_periods = len(portfolio_returns)
    annualized_return = (1.0 + holding_total_return) ** (252.0 / max(1, num_periods)) - 1.0
    annualized_volatility = float(portfolio_returns.std(ddof=1) * np.sqrt(252.0)) if num_periods > 1 else 0.0

    # Alpha and Beta vs SPY
    alpha = None
    beta = None
    annualized_benchmark_return = None
    if spy_close is not None and not spy_close.empty:
        market_returns = spy_close.pct_change().dropna()
        market_returns.name = 'market'
        if len(market_returns) > 252*2:
            market_returns = market_returns.tail(252*2)
        aligned = pd.concat([portfolio_returns, market_returns], axis=1, join='inner').dropna()
        aligned.columns = ['portfolio', 'market']
        if len(aligned) > 1 and aligned['market'].std(ddof=1) > 0:
            slope, intercept, r_value, p_value, std_err = linregress(aligned['market'].values, aligned['portfolio'].values)
            beta = float(slope)
            # Annualized alpha: daily intercept times 252 trading days
            alpha = float(intercept * 252)
            # Benchmark annualized return for Information Ratio
            bench_total = float((1.0 + aligned['market']).prod() - 1.0)
            annualized_benchmark_return = (1.0 + bench_total) ** (252.0 / len(aligned['market'])) - 1.0

    # Risk-adjusted metrics
    sharpe_ratio = None
    sortino_ratio = None
    if annualized_volatility and annualized_volatility > 0:
        sharpe_ratio = float((annualized_return - risk_free_rate) / annualized_volatility)

    # Sortino ratio uses downside deviation (returns below risk-free rate)
    daily_rf_rate = (1 + risk_free_rate) ** (1/252) - 1
    downside_returns = portfolio_returns[portfolio_returns < daily_rf_rate]
    downside_vol_ann = float(downside_returns.std(ddof=1) * np.sqrt(252.0)) if len(downside_returns) > 1 else 0.0
    if downside_vol_ann > 0:
        sortino_ratio = float((annualized_return - risk_free_rate) / downside_vol_ann)

    # Max drawdown
    cumulative = (1.0 + portfolio_returns).cumprod()
    rolling_peak = cumulative.cummax()
    drawdown = (cumulative - rolling_peak) / rolling_peak
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    # Additional risk/performance metrics
    # 1-day 95% historical VaR (positive indicates loss magnitude)
    var_95 = float(-np.percentile(portfolio_returns.values, 5)) if len(portfolio_returns) > 0 else 0.0

    # Upside Potential Ratio (threshold MAR = 0)
    if len(portfolio_returns) > 0:
        losses = np.minimum(portfolio_returns.values, 0.0)
        downside_semidev_daily = float(np.sqrt(np.mean(np.square(losses)))) if np.any(losses) else 0.0
        upside_potential_daily = float(np.mean(np.maximum(portfolio_returns.values, 0.0)))
        upside_potential_ratio = float(upside_potential_daily / downside_semidev_daily) if downside_semidev_daily > 0 else None
    else:
        upside_potential_ratio = None

    # Calmar Ratio: annualized return divided by absolute max drawdown
    calmar_ratio = float(annualized_return / abs(max_drawdown)) if max_drawdown != 0 else None

    # Information Ratio: (annualized portfolio return - annualized benchmark return) / annualized tracking error
    information_ratio = None
    if annualized_benchmark_return is not None:
        # active returns use the same aligned window built above
        aligned_for_active = pd.concat([portfolio_returns, market_returns], axis=1, join='inner').dropna()
        # Column names ensured via series names above
        active_returns = aligned_for_active['portfolio'] - aligned_for_active['market']
        tracking_error_ann = float(active_returns.std(ddof=1) * np.sqrt(252.0)) if len(active_returns) > 1 else 0.0
        if tracking_error_ann > 0:
            information_ratio = float((annualized_return - annualized_benchmark_return) / tracking_error_ann)

    metrics = {
        'holding_period_days': num_periods,
        'holding_period_years': f"{num_periods / 252.0:.2f}",
        'total_return': f"{holding_total_return * 100.0:.2f}%",
        'annualized_return': f"{annualized_return * 100.0:.2f}%",
        'annualized_volatility': f"{annualized_volatility * 100.0:.2f}%",
        'alpha': alpha,
        'beta': None if beta is None else float(f"{beta:.2f}"),
        'sharpe_ratio': None if sharpe_ratio is None else float(f"{sharpe_ratio:.2f}"),
        'sortino_ratio': None if sortino_ratio is None else float(f"{sortino_ratio:.2f}"),
        'max_drawdown': f"{max_drawdown * 100.0:.2f}%",
        'var_95': f"{var_95 * 100.0:.2f}%",
        'upside_potential_ratio': None if upside_potential_ratio is None else float(f"{upside_potential_ratio:.2f}"),
        'calmar_ratio': None if calmar_ratio is None else float(f"{calmar_ratio:.2f}"),
        'information_ratio': None if information_ratio is None else float(f"{information_ratio:.2f}"),
    }

    return {
        'per_ticker_total_returns': per_ticker_total_returns_pct,
        'portfolio_metrics': metrics,
    }

def get_most_recent_fundamentals(ticker: str, fundamentals_type: str) -> dict:
    """
    Get the most recent fundamentals for a ticker.
    """
    session = MarketSession()

    if fundamentals_type == 'balance_sheet':
        fundamentals = session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == ticker).order_by(BalanceSheet.date.desc()).limit(1).all()
    elif fundamentals_type == 'income_statement':
        fundamentals = session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == ticker).order_by(IncomeStatement.date.desc()).limit(1).all()
    elif fundamentals_type == 'cash_flow_statement':
        fundamentals = session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == ticker).order_by(CashFlowStatement.date.desc()).limit(1).all()
    elif fundamentals_type == 'financial_ratios':
        fundamentals = session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == ticker).order_by(FinancialRatio.date.desc()).limit(1).all()
    elif fundamentals_type == 'analyst_estimates':
        fundamentals = session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == ticker).order_by(AnalystEstimate.date.desc()).limit(1).all()
    elif fundamentals_type == 'all':
        fundamentals = {}
        fundamentals['balance_sheet'] = session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == ticker).order_by(BalanceSheet.date.desc()).limit(1).all()
        fundamentals['income_statement'] = session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == ticker).order_by(IncomeStatement.date.desc()).limit(1).all()
        fundamentals['cash_flow_statement'] = session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == ticker).order_by(CashFlowStatement.date.desc()).limit(1).all()
        fundamentals['financial_ratios'] = session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == ticker).order_by(FinancialRatio.date.desc()).limit(1).all()
        fundamentals['analyst_estimates'] = session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == ticker).order_by(AnalystEstimate.date.desc()).limit(1).all()
    else:
        raise ValueError(f"Invalid fundamentals type: {fundamentals_type}")
    
    session.close()

    if fundamentals_type == 'all':
        cleaned = {}
        keys_to_remove = {'ticker_id', 'link', 'finalLink'}
        for key, value in fundamentals.items():
            serialized_list = [serialize_sqlalchemy_obj(f) for f in value]
            cleaned[key] = [
                {k: v for k, v in item.items() if k not in keys_to_remove}
                for item in serialized_list
            ]
        return cleaned
    else:
        keys_to_remove = {'ticker_id', 'link', 'finalLink'}
        serialized_list = [serialize_sqlalchemy_obj(f) for f in fundamentals]
        cleaned_list = [
            {k: v for k, v in item.items() if k not in keys_to_remove}
            for item in serialized_list
        ]
        return cleaned_list

def get_initial_portfolio_data():
    """
    Get the initial portfolio stress test and performance analysis from the CIO agent.
    """
    initial_portfolio_dict = {
        # Long positions
        "CASY": {"conviction": 0.10, "position": "long"},
        "CELH": {"conviction": 0.10, "position": "long"},
        "ODC": {"conviction": 0.05, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.05, "position": "long"},
        "VITL": {"conviction": 0.05, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.05, "position": "long"},
        "COCO": {"conviction": 0.05, "position": "long"},
        "MNST": {"conviction": 0.05, "position": "long"},
        "CL": {"conviction": 0.05, "position": "long"},
        "IPAR": {"conviction": 0.05, "position": "long"},
        "TPB": {"conviction": 0.05, "position": "long"},
        "DOLE": {"conviction": 0.05, "position": "long"},
        "PPC": {"conviction": 0.05, "position": "long"},
        "INGR": {"conviction": 0.05, "position": "long"},
        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.02, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.05, "position": "short"},
        "MGPI": {"conviction": 0.05, "position": "short"},
        "ENR": {"conviction": 0.05, "position": "short"},
        "SPB": {"conviction": 0.05, "position": "short"},
        "COTY": {"conviction": 0.05, "position": "short"},
        "KVUE": {"conviction": 0.05, "position": "short"},
        "KLG": {"conviction": 0.05, "position": "short"},
        "JJSF": {"conviction": 0.05, "position": "short"},
        "SEB": {"conviction": 0.05, "position": "short"}
    }

    initial_stress_test_results = run_stress_test_workflow(initial_portfolio_dict)
    initial_upside_downside_ratios = get_upside_downside_ratios(initial_portfolio_dict)

    return {
        "initial_stress_test_results": initial_stress_test_results,
        "initial_upside_downside_ratios": initial_upside_downside_ratios
    }
    
def get_initial_portfolio_dict():
    """
    Get the initial portfolio dictionary.
    """
    # Long positions
    initial_portfolio_dict = {
        # Long positions
        "CASY": {"conviction": 0.10, "position": "long"},
        "CELH": {"conviction": 0.10, "position": "long"},
        "ODC": {"conviction": 0.05, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.05, "position": "long"},
        "VITL": {"conviction": 0.05, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.05, "position": "long"},
        "COCO": {"conviction": 0.05, "position": "long"},
        "MNST": {"conviction": 0.05, "position": "long"},
        "CL": {"conviction": 0.05, "position": "long"},
        "IPAR": {"conviction": 0.05, "position": "long"},
        "TPB": {"conviction": 0.05, "position": "long"},
        "DOLE": {"conviction": 0.05, "position": "long"},
        "PPC": {"conviction": 0.05, "position": "long"},
        "INGR": {"conviction": 0.05, "position": "long"},
        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.02, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.05, "position": "short"},
        "MGPI": {"conviction": 0.05, "position": "short"},
        "ENR": {"conviction": 0.05, "position": "short"},
        "SPB": {"conviction": 0.05, "position": "short"},
        "COTY": {"conviction": 0.05, "position": "short"},
        "KVUE": {"conviction": 0.05, "position": "short"},
        "KLG": {"conviction": 0.05, "position": "short"},
        "JJSF": {"conviction": 0.05, "position": "short"},
        "SEB": {"conviction": 0.05, "position": "short"}
    }

    return initial_portfolio_dict

def get_larger_ticker_pool():
    """
    Get the larger pool of tickers from the CIO agent's original selection.
    """
    session = ProphitAltsSession()
    fund = session.query(Fund).filter(Fund.fund_name == "consumer_staples_fund").first()
    fund_id = fund.id
    positions = session.query(FundInitialPosition).filter(FundInitialPosition.fund_id == fund_id).all()
    session.close()

    ticker_choices = {}

    for position in positions:
        ticker_choices[position.ticker_name] = {
            "position": position.position.value,
            "industry": position.industry,
            "risk_allocation": position.risk_allocation,
            "reasoning": position.reasoning
        }

    return ticker_choices

def calculate_correlation_matrix(portfolio_dict: dict = None) -> dict:
    """
    Calculate the correlation matrix for the given portfolio.
    """
    
    portfolio_dict = {
        'aapl': {'weight': 0.1, 'position': 'long'},
        'msft': {'weight': 0.2, 'position': 'long'},
        'goog': {'weight': 0.1, 'position': 'long'},
        'amzn': {'weight': 0.1, 'position': 'long'},
        'tsla': {'weight': 0.1, 'position': 'long'},
        'nvda': {'weight': 0.1, 'position': 'long'},
        'meta': {'weight': 0.1, 'position': 'long'},
    }

    # Get tickers from portfolio
    tickers = list(portfolio_dict.keys())
    
    # Get price data for last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252)
    
    # Fetch price data for all tickers
    prices_map = fetch_bulk_price_data_for_tickers(tickers, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), frequency='daily')
    
    if not prices_map:
        return {"error": "No price data available"}
    
    # Create DataFrame and calculate returns
    prices_df = pd.DataFrame(prices_map)
    returns_df = prices_df.pct_change().dropna()
    
    # Calculate correlation matrix
    correlation_matrix = returns_df.corr()
    
    # Round all values to 3 decimal places
    correlation_matrix = correlation_matrix.round(3)
    
    # Convert to dictionary format
    result = {
        'tickers': tickers,
        'correlation_matrix': correlation_matrix.to_dict()
    }
    
    return result

def calculate_covariance_matrix(portfolio_dict: dict = None) -> dict:
    """
    Calculate the covariance matrix for the given portfolio.
    """
    
    portfolio_dict = {
        'aapl': {'weight': 0.1, 'position': 'long'},
        'msft': {'weight': 0.2, 'position': 'long'},
        'goog': {'weight': 0.1, 'position': 'long'},
        'amzn': {'weight': 0.1, 'position': 'long'},
        'tsla': {'weight': 0.1, 'position': 'long'},
        'nvda': {'weight': 0.1, 'position': 'long'},
        'meta': {'weight': 0.1, 'position': 'long'},
    }

    # Get tickers from portfolio
    tickers = list(portfolio_dict.keys())
    
    # Get price data for last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252)
    
    # Fetch price data for all tickers
    prices_map = fetch_bulk_price_data_for_tickers(tickers, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), frequency='daily')
    
    if not prices_map:
        return {"error": "No price data available"}
    
    # Create DataFrame and calculate returns
    prices_df = pd.DataFrame(prices_map)
    returns_df = prices_df.pct_change().dropna()
    
    # Calculate covariance matrix
    covariance_matrix = returns_df.cov()
    
    # Round all values to 6 decimal places (covariance values are typically smaller)
    covariance_matrix = covariance_matrix.round(6)
    
    # Convert to dictionary format
    result = {
        'tickers': tickers,
        'covariance_matrix': covariance_matrix.to_dict()
    }
    
    return result

if __name__ == "__main__":
    print(calculate_correlation_matrix())
    print(calculate_covariance_matrix())