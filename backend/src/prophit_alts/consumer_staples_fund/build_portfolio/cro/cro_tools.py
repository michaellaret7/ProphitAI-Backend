from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
from backend.src.utils.validation_utils import validate_portfolio_dict
from backend.src.utils.token_count import get_token_count

# Consumer Staples Fund initial portfolio configuration
INITIAL_PORTFOLIO_DICT = {
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


def get_initial_portfolio_dict():
    """
    Get the initial portfolio dictionary.
    """
    return INITIAL_PORTFOLIO_DICT


def calculate_correlation_matrix(portfolio_dict: dict = None) -> dict:
    """
    Calculate the correlation matrix for the given portfolio.
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = validate_portfolio_dict(portfolio_dict)
    except ValueError as e:
        return {"error": str(e)}

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
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = validate_portfolio_dict(portfolio_dict)
    except ValueError as e:
        return {"error": str(e)}

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


def _get_portfolio_returns_data(tickers: list, days_back: int = 252) -> pd.DataFrame:
    """
    Helper function to get returns data for portfolio tickers.
    
    Parameters:
    - tickers: List of ticker symbols
    - days_back: Number of days to fetch (default 365)
    
    Returns:
    - DataFrame with returns data for each ticker
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Fetch price data
    prices_map = fetch_bulk_price_data_for_tickers(
        tickers, 
        start_date.strftime('%Y-%m-%d'), 
        end_date.strftime('%Y-%m-%d'), 
        frequency='daily'
    )
    
    if not prices_map:
        return pd.DataFrame()
    
    # Create DataFrame and calculate returns
    prices_df = pd.DataFrame(prices_map)
    returns_df = prices_df.pct_change().dropna()
    
    return returns_df


def vol_es(portfolio_dict: dict = None, horizon_days: int = 1, conf: float = 0.99, method: str = 'param') -> dict:
    """
    Calculate Volatility, Value at Risk (VaR), and Expected Shortfall (ES) for portfolio.
    
    Parameters:
    - portfolio_dict: Portfolio configuration with tickers and convictions
    - horizon_days: Time horizon for risk calculation (default: 1 day)
    - conf: Confidence level (default: 0.99 for 99% confidence)
    - method: Calculation method {'param', 'hist', 'ewma'}
    
    Returns:
    - VaR: Value at Risk at specified confidence level
    - ES: Expected Shortfall (conditional VaR)
    - vol: Portfolio volatility (annualized)
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = validate_portfolio_dict(portfolio_dict)
    except ValueError as e:
        return {"error": str(e)}

    # Get tickers and weights from portfolio
    tickers = list(portfolio_dict.keys())
    weights = np.array([portfolio_dict[ticker]['conviction'] * (1 if portfolio_dict[ticker]['position'] == 'long' else -1) 
                       for ticker in tickers])
    
    try:
        # Get returns data
        returns_df = _get_portfolio_returns_data(tickers)
        
        if returns_df.empty:
            return {"error": "No price data available for portfolio tickers"}
        
        # Calculate portfolio returns
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        # Calculate covariance matrix
        cov_matrix = returns_df.cov()
        
        # Portfolio variance and volatility
        portfolio_variance = np.dot(weights, np.dot(cov_matrix.values, weights))
        portfolio_vol_daily = np.sqrt(portfolio_variance)
        portfolio_vol_annual = portfolio_vol_daily * np.sqrt(252)
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(conf)
        
        # Calculate VaR and ES based on method
        if method == 'param':
            # Parametric VaR
            var_1day = z_score * portfolio_vol_daily
            
            # Parametric ES
            alpha = 1 - conf
            es_value = portfolio_vol_daily * stats.norm.pdf(stats.norm.ppf(alpha)) / alpha
            
        elif method == 'hist':
            # Historical VaR
            var_1day = -np.percentile(portfolio_returns, (1 - conf) * 100)
            
            # Historical ES
            var_threshold = var_1day
            tail_losses = portfolio_returns[portfolio_returns <= -var_threshold]
            es_value = -tail_losses.mean() if len(tail_losses) > 0 else var_1day
            
        elif method == 'ewma':
            # EWMA implementation using exponentially weighted covariance
            lambda_param = 0.94  # Standard EWMA decay factor
            
            # Calculate EWMA covariance matrix
            ewma_cov = returns_df.ewm(alpha=1-lambda_param).cov().iloc[-len(tickers):, -len(tickers):]
            
            # Portfolio variance using EWMA covariance
            portfolio_var_ewma = np.dot(weights, np.dot(ewma_cov.values, weights))
            portfolio_vol_daily_ewma = np.sqrt(portfolio_var_ewma)
            portfolio_vol_annual = portfolio_vol_daily_ewma * np.sqrt(252)
            
            # EWMA VaR
            var_1day = z_score * portfolio_vol_daily_ewma
            
            # EWMA ES
            alpha = 1 - conf
            es_value = portfolio_vol_daily_ewma * stats.norm.pdf(stats.norm.ppf(alpha)) / alpha
            
            portfolio_vol_daily = portfolio_vol_daily_ewma
            
        else:
            return {"error": f"Invalid method '{method}'. Use 'param', 'hist', or 'ewma'"}
        
        # Scale VaR for time horizon
        var_scaled = abs(var_1day) * np.sqrt(horizon_days)
        es_scaled = abs(es_value) * np.sqrt(horizon_days)
        var_annual = abs(var_1day) * np.sqrt(252)
        
        result = {
            'method': method,
            'confidence_level': conf,
            'horizon_days': horizon_days,
            'VaR': round(var_scaled, 6),
            'ES': round(es_scaled, 6),
            'vol': round(portfolio_vol_annual, 6),
            'var_1day': round(abs(var_1day), 6),
            'var_annual': round(var_annual, 6)
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate vol_es: {str(e)}"}


def risk_contribution(portfolio_dict: dict = None, metric: str = 'vol') -> dict:
    """
    Calculate Total Risk and risk contributions by asset.
    
    Parameters:
    - portfolio_dict: Portfolio configuration with tickers and convictions
    - metric: Risk metric to decompose {'vol', 'var'}
    
    Returns:
    - TR: Total Risk (portfolio level)
    - MCTR: Marginal Contribution to Total Risk (per asset)
    - CTR_pct: Component Total Risk as percentage (per asset)
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = validate_portfolio_dict(portfolio_dict)
    except ValueError as e:
        return {"error": str(e)}

    # Get tickers and weights from portfolio
    tickers = list(portfolio_dict.keys())
    weights = np.array([portfolio_dict[ticker]['conviction'] * (1 if portfolio_dict[ticker]['position'] == 'long' else -1) 
                       for ticker in tickers])
    
    try:
        # Get returns data
        returns_df = _get_portfolio_returns_data(tickers)
        
        if returns_df.empty:
            return {"error": "No price data available for portfolio tickers"}
        
        # Calculate covariance matrix
        cov_matrix = returns_df.cov()
        
        if metric == 'vol':
            # Volatility-based risk contribution
            # Portfolio variance
            portfolio_variance = np.dot(weights, np.dot(cov_matrix.values, weights))
            total_risk = np.sqrt(portfolio_variance)  # Portfolio volatility
            
            # Marginal contribution to total risk (volatility)
            marginal_contrib = np.dot(cov_matrix.values, weights) / total_risk
            
            # Component contribution to total risk
            component_contrib = weights * marginal_contrib
            
            # Convert to percentages
            ctr_pct = (component_contrib / total_risk) * 100
            
        elif metric == 'var':
            # VaR-based risk contribution
            z_score = stats.norm.ppf(0.99)  # Default 99% confidence
            
            # Portfolio variance and volatility
            portfolio_variance = np.dot(weights, np.dot(cov_matrix.values, weights))
            portfolio_vol_daily = np.sqrt(portfolio_variance)
            
            # Total portfolio VaR
            total_risk = z_score * portfolio_vol_daily
            
            # Marginal VaR = (dVaR/dw_i) = (Σw * cov_i) / portfolio_vol * z_score
            marginal_contrib = np.dot(cov_matrix.values, weights) / portfolio_vol_daily * z_score
            
            # Component VaR = weight * marginal VaR
            component_contrib = weights * marginal_contrib
            
            # Convert to percentages
            ctr_pct = (component_contrib / total_risk) * 100
            
        else:
            return {"error": f"Invalid metric '{metric}'. Use 'vol' or 'var'"}
        
        # Build result dictionary
        result = {
            'metric': metric,
            'TR': round(float(total_risk), 6),
            'MCTR': {ticker: round(float(marginal_contrib[i]), 6) for i, ticker in enumerate(tickers)},
            'CTR_pct': {ticker: round(float(ctr_pct[i]), 2) for i, ticker in enumerate(tickers)}
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate risk_contribution: {str(e)}"}


def drawdown_profile(portfolio_dict: dict = None) -> dict:
    """
    Analyze portfolio drawdown characteristics.
    
    Parameters:
    - portfolio_dict: Portfolio configuration with tickers and convictions
    
    Returns:
    - max_dd: Maximum drawdown (worst peak-to-trough decline)
    - avg_dd: Average drawdown across all episodes  
    - ulcer: Ulcer Index (measure of drawdown severity and duration)
    - episodes: List of drawdown episodes with start/end dates and recovery times
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = validate_portfolio_dict(portfolio_dict)
    except ValueError as e:
        return {"error": str(e)}

    # Get tickers and weights from portfolio
    tickers = list(portfolio_dict.keys())
    weights = {ticker: portfolio_dict[ticker]['conviction'] * (1 if portfolio_dict[ticker]['position'] == 'long' else -1) 
              for ticker in tickers}
    
    try:
        # Get returns data for last 2 years for better drawdown analysis
        returns_df = _get_portfolio_returns_data(tickers, days_back=504)
        
        if returns_df.empty:
            return {"error": "No price data available"}
        
        # Calculate weighted portfolio returns
        portfolio_returns = pd.Series(0, index=returns_df.index)
        for ticker in tickers:
            if ticker in returns_df.columns:
                portfolio_returns += returns_df[ticker] * weights[ticker]
        
        # Calculate cumulative portfolio value (NAV)
        portfolio_nav = (1 + portfolio_returns).cumprod()
        
        # Calculate running maximum (peak values)
        running_max = portfolio_nav.expanding().max()
        
        # Calculate drawdown series
        drawdown = (portfolio_nav - running_max) / running_max
        
        # Calculate key metrics
        max_drawdown = float(drawdown.min())
        
        # Find drawdown episodes
        episodes = []
        in_drawdown = False
        episode_start = None
        episode_peak = None
        
        for i, (date, dd_value) in enumerate(drawdown.items()):
            if not in_drawdown and dd_value < -0.001:  # Start of drawdown (>0.1% decline)
                in_drawdown = True
                episode_start = date
                episode_peak = running_max.iloc[i]
                
            elif in_drawdown and dd_value >= -0.001:  # End of drawdown
                if episode_start is not None:
                    episode_end = date
                    episode_trough = portfolio_nav.loc[episode_start:episode_end].min()
                    episode_max_dd = (episode_trough - episode_peak) / episode_peak
                    
                    # Calculate recovery time (days to get back to peak)
                    recovery_date = None
                    future_nav = portfolio_nav[episode_end:]
                    recovery_nav = future_nav[future_nav >= episode_peak]
                    if not recovery_nav.empty:
                        recovery_date = recovery_nav.index[0]
                        recovery_days = (recovery_date - episode_start).days
                    else:
                        recovery_days = None  # Not yet recovered
                    
                    episodes.append({
                        'start_date': episode_start.strftime('%Y-%m-%d'),
                        'end_date': episode_end.strftime('%Y-%m-%d'),
                        'max_drawdown': round(float(episode_max_dd), 4),
                        'duration_days': (episode_end - episode_start).days,
                        'recovery_days': recovery_days,
                        'recovered': recovery_days is not None
                    })
                
                in_drawdown = False
                episode_start = None
        
        # Calculate average drawdown
        if episodes:
            avg_drawdown = float(np.mean([ep['max_drawdown'] for ep in episodes]))
        else:
            avg_drawdown = 0.0
        
        # Calculate Ulcer Index (RMS of drawdowns)
        ulcer_index = float(np.sqrt((drawdown ** 2).mean()))
        
        result = {
            'analysis_period_days': len(portfolio_nav),
            'max_dd': round(max_drawdown, 4),
            'avg_dd': round(avg_drawdown, 4),
            'ulcer': round(ulcer_index, 4),
            'num_episodes': len(episodes),
            'episodes': episodes,
            'current_drawdown': round(float(drawdown.iloc[-1]), 4)
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate drawdown_profile: {str(e)}"}

#TODO: add an industry/subindustry concentration tool