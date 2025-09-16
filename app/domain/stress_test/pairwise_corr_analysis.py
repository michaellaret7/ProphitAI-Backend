import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from datetime import datetime, timedelta
from app.domain.stress_test.scenarios import historical_scenarios
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.utils.validation_utils import normalize_portfolio_input
from app.models.portfolio_models import PortfolioInput

def calculate_correlation_matrix(price_data: dict = None, start_date_str: str = None, end_date_str: str = None, frequency: str = None, tickers: list[str] = None):
    """
    Calculate the correlation matrix for the given price data, accounting for position sizes and directions.
    
    Parameters:
    - price_data: Dict mapping ticker symbols to price Series
    - start_date_str: Start date for the price data
    - end_date_str: End date for the price data
    - frequency: Frequency of the price data
    - tickers: List of ticker symbols
    Returns:
    - pd.DataFrame: Correlation matrix
    """

    if not price_data:
        price_data = fetch_bulk_price_data_for_tickers(tickers=tickers, start_date_str=start_date_str, end_date_str=end_date_str, frequency=frequency)

    # Convert dict of Series to DataFrame
    price_df = pd.DataFrame(price_data)

    # v2 returns and correlation
    returns_df = pd.DataFrame({
        col: ReturnsCalculator.daily_price_returns(price_df[col])
        for col in price_df.columns
    }).dropna()

    correlation_matrix = RiskCalculator.correlation_matrix(returns_df)

    np.fill_diagonal(correlation_matrix.values, np.nan)
        
    return correlation_matrix

def pairwise_correlation_analysis(correlation_matrix: pd.DataFrame):
    """
    Calculate the average correlation for each ticker.
    
    Parameters:
    - correlation_matrix: Correlation matrix DataFrame
    
    Returns:
    - dict: Dictionary mapping ticker symbols to their average correlations
    """
    # Calculate average correlation for each ticker (row-wise mean, excluding NaN diagonal)
    avg_correlations = {}
    
    for ticker in correlation_matrix.index:
        # Get the row for this ticker and calculate mean (NaN values are automatically excluded)
        avg_correlation = correlation_matrix.loc[ticker].mean()
        avg_correlations[ticker] = float(round(avg_correlation, 4))
    
    portfolio_average_correlation = sum(avg_correlations.values()) / len(avg_correlations)

    return avg_correlations, portfolio_average_correlation

def run_pairwise_correlation_analysis(portfolio_dict: PortfolioInput | dict):
    """
    Optimized pairwise correlation analysis that fetches all price data once.
    """
    baseline_summary = {}
    stress_summary = {}
    # Normalize/accept both PortfolioInput and dict
    try:
        norm = normalize_portfolio_input(portfolio_dict)
        tickers = list(norm.root.keys())
    except Exception:
        tickers = list(portfolio_dict.keys()) if isinstance(portfolio_dict, dict) else []

    # Prepare all date ranges needed
    baseline_start = (datetime.now() - timedelta(days=252)).strftime("%Y-%m-%d")
    baseline_end = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch baseline data once
    baseline_price_data = fetch_bulk_price_data_for_tickers(
        tickers=tickers, 
        start_date_str=baseline_start, 
        end_date_str=baseline_end, 
        frequency="daily"
    )
    
    # Calculate baseline correlation matrix using cached data
    baseline_correlation_matrix = calculate_correlation_matrix(
        price_data=baseline_price_data
    )
    avg_correlations, portfolio_average_correlation = pairwise_correlation_analysis(baseline_correlation_matrix)

    baseline_summary['baseline_scenario_averages'] = {
        'ticker_averages': avg_correlations,
        'average_portfolio_correlation': portfolio_average_correlation
    }

    # Fetch all stress scenario data in bulk
    stress_correlations_dict = {}
    
    for scenario_name, scenario_data in historical_scenarios.items():
        # Fetch stress scenario data
        stress_price_data = fetch_bulk_price_data_for_tickers(
            tickers=tickers,
            start_date_str=scenario_data['start_date'],
            end_date_str=scenario_data['end_date'],
            frequency='15mins'
        )
        
        # Calculate correlation matrix using fetched data
        stress_correlation_matrix = calculate_correlation_matrix(
            price_data=stress_price_data
        )
        
        avg_correlations, portfolio_average_correlation = pairwise_correlation_analysis(stress_correlation_matrix)
        stress_correlations_dict[scenario_name] = {
            'avg_correlations': avg_correlations, 
            'portfolio_average_correlation': portfolio_average_correlation
        }
    
    # Calculate average across all stress scenarios
    ticker_averages = {}
    portfolio_correlations = []
    
    # Get all tickers from the first scenario
    all_tickers = list(next(iter(stress_correlations_dict.values()))['avg_correlations'].keys())
    
    # Calculate average for each ticker across all scenarios
    for ticker in all_tickers:
        ticker_values = []
        for scenario_data in stress_correlations_dict.values():
            if ticker in scenario_data['avg_correlations']:
                ticker_values.append(scenario_data['avg_correlations'][ticker])
        ticker_averages[ticker] = round(sum(ticker_values) / len(ticker_values), 4) if ticker_values else 0
    
    # Calculate average portfolio correlation across all scenarios
    for scenario_data in stress_correlations_dict.values():
        portfolio_correlations.append(scenario_data['portfolio_average_correlation'])
    
    avg_portfolio_correlation = round(sum(portfolio_correlations) / len(portfolio_correlations), 4) if portfolio_correlations else 0
    
    # Create summary dictionary
    stress_summary['stress_scenario_averages'] = {
        'ticker_averages': ticker_averages,
        'average_portfolio_correlation': avg_portfolio_correlation
    }

    return baseline_summary, stress_summary


if __name__ == "__main__":
    # Example uses canonical schema with allocation/position
    portfolio = PortfolioInput({
        "CASY": {"allocation": 0.10, "position": "long"},
        "CELH": {"allocation": 0.10, "position": "long"},
        "ODC": {"allocation": 0.05, "position": "long"},
        "ODD": {"allocation": 0.05, "position": "long"},
        "PM": {"allocation": 0.05, "position": "long"},
        "VITL": {"allocation": 0.05, "position": "long"},
        "WMT": {"allocation": 0.05, "position": "long"},
        "BJ": {"allocation": 0.05, "position": "long"},
        "SFM": {"allocation": 0.05, "position": "long"},
        "COCO": {"allocation": 0.05, "position": "long"},
        "MNST": {"allocation": 0.05, "position": "long"},
        "CL": {"allocation": 0.05, "position": "long"},
        "IPAR": {"allocation": 0.05, "position": "long"},
        "TPB": {"allocation": 0.05, "position": "long"},
        "DOLE": {"allocation": 0.05, "position": "long"},
        "PPC": {"allocation": 0.05, "position": "long"},
        "INGR": {"allocation": 0.05, "position": "long"},
        "WBA": {"allocation": 0.05, "position": "short"},
        "ANDE": {"allocation": 0.05, "position": "short"}
    })

    baseline_summary, stress_summary = run_pairwise_correlation_analysis(portfolio)
    print(baseline_summary)
    print(stress_summary)

 