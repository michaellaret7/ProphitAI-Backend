import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.risk import RiskCalculator
from app.core.calculations.returns import ReturnsCalculator
from app.core.calculations.stress_test.scenarios import historical_scenarios, hypothetical_scenarios
from app.utils.validation_utils import normalize_portfolio_input
from app.models.portfolio_models import PortfolioInput

def calculate_dynamic_weights(portfolio_betas: dict, ticker: str) -> dict:
    """
    Calculate dynamic weights based on absolute beta values.
    Higher beta means more sensitivity to that factor.
    """
    etf_betas = portfolio_betas[ticker]
    
    # Use absolute values of betas as basis for weights
    abs_betas = {etf: abs(beta) for etf, beta in etf_betas.items()}
    total_abs_beta = sum(abs_betas.values())
    
    # Normalize to sum to 1 with robust error handling
    if total_abs_beta > 0 and np.isfinite(total_abs_beta):
        weights = {etf: abs_beta / total_abs_beta for etf, abs_beta in abs_betas.items()}
    else:
        # Fallback to equal weights if all betas are 0 or invalid
        num_etfs = len(etf_betas)
        if num_etfs > 0:
            weights = {etf: 1.0 / num_etfs for etf in etf_betas.keys()}
        else:
            # Ultimate fallback - empty weights
            weights = {}
    
    return weights

def get_portfolio_betas(portfolio: list, etf_shocks: dict, period_days: int = 252) -> dict:
    """
    Get the portfolio betas for a given portfolio and etf shocks.
    Uses bulk data fetching for efficiency with robust error handling.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Combine all tickers we need to fetch
    all_tickers = list(portfolio) + list(etf_shocks.keys())
    
    # Bulk fetch all price data at once
    print(f"Fetching price data for {len(all_tickers)} tickers...")
    price_data_map = fetch_bulk_price_data_for_tickers(
        all_tickers, 
        start_date_str, 
        end_date_str, 
        frequency='daily'
    )
    print(f"Price data fetched for {len(price_data_map)} tickers")
    
    # Calculate betas using the pre-fetched data with robust error handling
    portfolio_betas = {ticker: {etf: 0.0 for etf in etf_shocks.keys()} for ticker in portfolio}
    
    for ticker in portfolio:
        if ticker not in price_data_map:
            print(f"Warning: No price data found for {ticker} - setting all betas to 0.0")
            continue
            
        ticker_prices = price_data_map[ticker]
        
        # Validate ticker data has sufficient length
        if len(ticker_prices) < 2:
            print(f"Warning: Insufficient data for {ticker} ({len(ticker_prices)} points) - setting all betas to 0.0")
            continue
        
        for etf in etf_shocks.keys():
            if etf not in price_data_map:
                print(f"Warning: No price data found for ETF {etf} - setting beta to 0.0")
                continue
                
            etf_prices = price_data_map[etf]
            
            # Validate ETF data has sufficient length
            if len(etf_prices) < 2:
                print(f"Warning: Insufficient data for ETF {etf} ({len(etf_prices)} points) - setting beta to 0.0")
                continue
            
            try:
                # Calculate beta using calculations_v2 utilities on daily returns
                ticker_returns = ReturnsCalculator.daily_price_returns(ticker_prices)
                etf_returns = ReturnsCalculator.daily_price_returns(etf_prices)
                
                # Validate returns data
                if ticker_returns.empty or etf_returns.empty:
                    print(f"Warning: Empty returns data for {ticker} vs {etf} - setting beta to 0.0")
                    continue
                
                beta_value = RiskCalculator.beta(ticker_returns, etf_returns)
                
                # Handle NaN, infinity, or invalid beta values
                if pd.isna(beta_value) or not np.isfinite(beta_value):
                    beta_value = 0.0
                    print(f"Warning: Invalid beta value for {ticker} vs {etf} - setting to 0.0")
                
                portfolio_betas[ticker][etf] = round(float(beta_value), 3)
                
            except Exception as e:
                print(f"Warning: Error calculating beta for {ticker} vs {etf}: {e} - setting beta to 0.0")
                portfolio_betas[ticker][etf] = 0.0
    
    return portfolio_betas

def compute_shock_returns(portfolio_betas: dict, etf_shocks: dict, portfolio_dict: dict):
    """
    Compute the shock returns for a portfolio based on the baseline betas and etf shocks.
    Inverts returns for short positions.
    """
    shock_returns = {ticker: {etf: 0.0 for etf in etf_shocks.keys()} for ticker in portfolio_betas.keys()}

    for ticker, etf_betas in portfolio_betas.items():
        # Get position type (default to 'long' if not specified)
        position = portfolio_dict.get(ticker, {}).get('position', 'long')
        
        for etf, beta in etf_betas.items():
            shock = etf_shocks[etf]  # Direct access instead of etf_shocks[etf]['shock']
            base_return = beta * shock
            
            # Invert return for short positions
            if position == 'short':
                base_return = -base_return
                
            shock_returns[ticker][etf] = round(float(base_return), 3)

    return shock_returns

def get_stock_return(shock_returns: dict, portfolio_betas: dict) -> dict:
    """
    For each ticker, multiply each ETF shock by its DYNAMIC weight and
    return a flat dict {ticker: sum_of_weighted_etf_shocks} rounded to 2 decimals (percent).
    """
    summed_returns = {}

    for ticker, etf_returns in shock_returns.items():
        try:
            # Calculate dynamic weights for this specific ticker
            dynamic_weights = calculate_dynamic_weights(portfolio_betas, ticker)
            
            # Handle case where dynamic weights are empty
            if not dynamic_weights:
                print(f"Warning: No dynamic weights available for {ticker} - setting return to 0.0%")
                summed_returns[ticker] = 0.0
                continue
            
            total_weighted = 0.0
            for etf, shock_return in etf_returns.items():
                # Use dynamic weight with fallback to 0 if not found
                weight = dynamic_weights.get(etf, 0.0)
                total_weighted += shock_return * weight
            
            # Validate the result before converting to percentage
            if not np.isfinite(total_weighted):
                print(f"Warning: Invalid total_weighted value for {ticker} - setting return to 0.0%")
                summed_returns[ticker] = 0.0
            else:
                # Multiply first to convert to percent, then round to 2 decimals to avoid float tails
                summed_returns[ticker] = round(float(total_weighted) * 100.0, 2)
                
        except Exception as e:
            print(f"Warning: Error calculating stock return for {ticker}: {e} - setting return to 0.0%")
            summed_returns[ticker] = 0.0

    return summed_returns

def run_stress_test_engine(portfolio: PortfolioInput | dict, etf_shocks: dict, pre_calculated_betas: dict = None):
    """
    Run the stress test engine.
    
    Parameters:
    - portfolio: PortfolioInput or compatible dict mapping ticker -> {allocation, position}
    - etf_shocks: Dictionary with ETF tickers as keys and shock values (decimals) as values
    - pre_calculated_betas: Optional pre-calculated betas to avoid redundant fetching
    
    Returns:
    - dict: Contains expected_returns, betas, and shock_returns
    """
    # Normalize portfolio to canonical schema
    normalized = normalize_portfolio_input(portfolio)
    normalized_dict = {
        t: {"allocation": float(p.allocation), "position": p.position.value}
        for t, p in normalized.root.items()
    }
    tickers = list(normalized.root.keys())
    # Use pre-calculated betas if provided, otherwise fetch them
    if pre_calculated_betas is not None:
        betas = pre_calculated_betas
    else:
        betas = get_portfolio_betas(tickers, etf_shocks)
    
    shock_returns = compute_shock_returns(betas, etf_shocks, normalized_dict)
    expected_returns = get_stock_return(shock_returns, betas)

    return {
        'expected_returns': expected_returns,
        'betas': betas,
        'shock_returns': shock_returns
    }


if __name__ == "__main__":
    portfolio = PortfolioInput({
        "AAPL": {"allocation": 0.05, "position": "long"},
        "WBA": {"allocation": 0.03, "position": "short"},
    })
    etf_shocks = {
        "SPY": 0.05,
    }
    print(run_stress_test_engine(portfolio, etf_shocks))