import pandas as pd
import numpy as np
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
from datetime import datetime, timedelta
from backend.src.stress_test.simulated_shocks.scenarios import historical_scenarios

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
    
    # Calculate returns for correlation (using percentage change)
    returns_df = price_df.pct_change().dropna()
    
    # Calculate correlation matrix
    correlation_matrix = returns_df.corr()

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

def run_pairwise_correlation_analysis(portfolio_dict: dict):
    baseline_summary = {}
    stress_summary = {}
    tickers = list(portfolio_dict.keys())

    start_date_str = (datetime.now() - timedelta(days=252)).strftime("%Y-%m-%d")
    end_date_str = datetime.now().strftime("%Y-%m-%d")  
    frequency = "daily"

    baseline_correlation_matrix = calculate_correlation_matrix(tickers=tickers, start_date_str=start_date_str, end_date_str=end_date_str, frequency=frequency)
    avg_correlations, portfolio_average_correlation = pairwise_correlation_analysis(baseline_correlation_matrix)

    baseline_summary['baseline_scenario_averages'] = {
        'ticker_averages': avg_correlations,
        'average_portfolio_correlation': portfolio_average_correlation
    }

    # Calculate stress scenario correlations
    stress_correlations_dict = {}
    
    for scenario in historical_scenarios.keys():
        stress_correlation_matrix = calculate_correlation_matrix(tickers=tickers, start_date_str=historical_scenarios[scenario]['start_date'], end_date_str=historical_scenarios[scenario]['end_date'], frequency='15mins')
        avg_correlations, portfolio_average_correlation = pairwise_correlation_analysis(stress_correlation_matrix)
        stress_correlations_dict[scenario] = {'avg_correlations': avg_correlations, 'portfolio_average_correlation': portfolio_average_correlation}
    
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
    portfolio_dict = {
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

    baseline_summary, stress_summary = run_pairwise_correlation_analysis(portfolio_dict)
    print(baseline_summary)
    print(stress_summary)

 