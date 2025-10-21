# Import existing risk calculators
from datetime import datetime, timedelta
from app.core.calculations.risk.calculator import RiskCalculator
import numpy as np

def calculate_market_risk(ticker, price_data, market_data, lookback_days=252):
    """
    Calculate comprehensive market risk metrics for a ticker using pre-fetched data.

    This function follows the separation of concerns principle: it performs calculations
    only, without fetching data. For portfolio-level analysis, fetch data in bulk using
    fetch_bulk_ohlcv_data_for_tickers() before calling this function.

    Metrics calculated:
    - Annualized Volatility
    - Historical VaR (95% and 99%)
    - Expected Shortfall (CVaR)
    - Beta to market
    - Max Drawdown
    - Ulcer Index

    Args:
        ticker: Stock ticker symbol
        price_data: DataFrame with 'close' column for the ticker
        market_data: DataFrame with 'close' column for market benchmark (e.g., SPY)
        lookback_days: Days of historical data used (default 252 = 1 year)

    Returns:
        Dict with market risk metrics and normalized score (0-1)

    Example:
        >>> from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
        >>> bulk_data = fetch_bulk_ohlcv_data_for_tickers(['AAPL', 'SPY'], '2024-01-01', '2024-12-31')
        >>> result = calculate_market_risk('AAPL', bulk_data['AAPL'], bulk_data['SPY'])
    """
    # Validate input data
    if price_data is None or price_data.empty:
        return {'error': f'No price data available for {ticker}'}
    
    # Calculate daily returns
    daily_returns = price_data['close'].pct_change().dropna()
    
    # 1. Annualized Volatility
    volatility = RiskCalculator.annualized_volatility(daily_returns)
    
    # 2. Historical VaR (95% and 99%)
    var_95 = RiskCalculator.historical_var(daily_returns, confidence=0.95)
    var_99 = RiskCalculator.historical_var(daily_returns, confidence=0.99)
    
    # 3. Expected Shortfall (CVaR)
    cvar_95 = RiskCalculator.expected_shortfall(daily_returns, confidence=0.95)
    cvar_99 = RiskCalculator.expected_shortfall(daily_returns, confidence=0.99)
    
    # 4. Beta to market
    if market_data is not None and not market_data.empty:
        market_returns = market_data['close'].pct_change().dropna()
        beta = RiskCalculator.beta(daily_returns, market_returns)
        up_beta, down_beta = RiskCalculator.up_down_beta(daily_returns, market_returns)
    else:
        beta = np.nan
        up_beta, down_beta = np.nan, np.nan
    
    # 5. Max Drawdown
    max_dd = RiskCalculator.max_drawdown(price_data['close'])
    
    # 6. Ulcer Index (downside volatility)
    ulcer = RiskCalculator.ulcer_index(price_data['close'])

    # =========================================================================
    # MARKET RISK SCORING
    # =========================================================================
    # Component Weights:
    # - Volatility: 40% (PRIMARY - price risk)
    # - VaR/CVaR: 30% (Tail risk and downside exposure)
    # - Beta: 20% (Market sensitivity)
    # - Drawdown Metrics: 10% (Historical loss severity)

    normalized = {}

    # 1. Volatility (40% weight) - PRIMARY indicator
    # Benchmark: <15% = low, 15-25% = moderate, 25-40% = high, 40%+ = very high
    if not np.isnan(volatility):
        if volatility < 0.15:
            vol_score = 0.2
        elif volatility < 0.25:
            vol_score = 0.4
        elif volatility < 0.40:
            vol_score = 0.6
        else:
            # Scale linearly above 40%, cap at 1.0
            vol_score = min(0.8 + (volatility - 0.40) * 0.5, 1.0)
        normalized['volatility'] = vol_score
    else:
        normalized['volatility'] = 0.5  # Default if unavailable

    # 2. VaR 99% (15% weight) - Tail risk exposure
    # Benchmark: 2% = low, 5% = moderate, 10%+ = high
    if not np.isnan(var_99):
        normalized['var_99'] = min(abs(var_99) / 0.10, 1.0)

    # 3. CVaR 99% (15% weight) - Expected shortfall beyond VaR
    # Benchmark: 3% = low, 6% = moderate, 12%+ = high
    if not np.isnan(cvar_99):
        normalized['cvar_99'] = min(abs(cvar_99) / 0.12, 1.0)

    # 4. Beta (20% weight) - Market sensitivity
    # Benchmark: Beta deviation from 1.0 indicates systematic risk
    # 0.8-1.2 = normal, <0.5 or >2.0 = high deviation
    if not np.isnan(beta):
        beta_deviation = abs(beta - 1.0)
        normalized['beta'] = min(beta_deviation / 1.5, 1.0)
    else:
        normalized['beta'] = 0.5  # Default if unavailable

    # 5. Max Drawdown (5% weight) - Historical loss severity
    # Benchmark: -10% = low, -25% = moderate, -50%+ = severe
    if not np.isnan(max_dd):
        normalized['max_drawdown'] = min(abs(max_dd) / 0.50, 1.0)
    else:
        normalized['max_drawdown'] = 0.5

    # 6. Ulcer Index (5% weight) - Downside volatility
    # Benchmark: 5% = low, 15% = moderate, 30%+ = high
    if not np.isnan(ulcer):
        normalized['ulcer_index'] = min(ulcer / 0.30, 1.0)
    else:
        normalized['ulcer_index'] = 0.5

    # Weighted composite score
    weights = {
        'volatility': 0.40,      # PRIMARY - price risk
        'var_99': 0.15,          # Tail risk
        'cvar_99': 0.15,         # Expected shortfall (VaR/CVaR = 30% total)
        'beta': 0.20,            # Market sensitivity
        'max_drawdown': 0.05,    # Historical severity
        'ulcer_index': 0.05      # Downside volatility (Drawdown = 10% total)
    }

    # Calculate weighted average
    total_score = 0.0
    total_weight = 0.0

    for metric, weight in weights.items():
        if metric in normalized:
            total_score += normalized[metric] * weight
            total_weight += weight

    # Normalize by actual total weight (handles missing metrics gracefully)
    if total_weight > 0:
        market_risk_score = total_score / total_weight
    else:
        market_risk_score = np.nan

    return {
        'ticker': ticker,
        'market_risk_score': market_risk_score,
        'normalized_components': normalized,  # Show individual normalized scores
        'metrics': {
            'annualized_volatility': volatility,
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99,
            'beta': beta,
            'up_beta': up_beta,
            'down_beta': down_beta,
            'max_drawdown': max_dd,
            'ulcer_index': ulcer
        }
    }

