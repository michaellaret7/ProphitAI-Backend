from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from app.utils.gpt_parser import canonical_portfolio
from app.models.portfolio_models import PortfolioInput
from app.db.core.db_config import ProphitAltsSession
from app.db.core.prophit_alts_models import FundInitialPosition, Fund
from app.utils.decorators.database import with_session

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


@with_session('prophit')
def get_initial_portfolio_dict(session=None):
    """
    Get the initial portfolio dictionary.
    """
    initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

    INITIAL_PORTFOLIO_DICT = {}

    for position in initial_positions:
        INITIAL_PORTFOLIO_DICT[position.ticker_name] = {
            "conviction": position.conviction,
            "position": position.position.value
        }
    
    INITIAL_PORTFOLIO_DICT = {t: {"allocation": float(p.conviction), "position": p.position.value} for t, p in INITIAL_PORTFOLIO_DICT.items()}

    return INITIAL_PORTFOLIO_DICT   

def calculate_covariance_matrix(portfolio_dict: PortfolioInput | dict = None) -> dict:
    """
    Calculate the covariance matrix for the given portfolio.
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return {"error": str(e)}

    # Get tickers from portfolio
    tickers = list(portfolio_dict.keys())
    
    # Use utility to get portfolio data
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio=portfolio_dict,
        lookback_days=252,
        include_dividends=False  # Don't need dividends for covariance
    )
    
    if not price_data:
        return {"error": "No price data available"}
    
    # Calculate returns for each ticker
    returns_df = pd.DataFrame({
        ticker: ReturnsCalculator.daily_price_returns(prices)
        for ticker, prices in price_data.items()
        if prices is not None and not prices.empty
    }).dropna()
    
    if returns_df.empty:
        return {"error": "No price data available"}
    
    # Calculate covariance matrix using calculations_v2 (daily)
    covariance_matrix = RiskCalculator.covariance_matrix(returns_df, annualize=False)
    
    # Round all values to 6 decimal places (covariance values are typically smaller)
    covariance_matrix = covariance_matrix.round(6)
    
    # Convert to dictionary format
    result = {
        'tickers': tickers,
        'covariance_matrix': covariance_matrix.to_dict()
    }
    
    return result

def vol_es(portfolio_dict: PortfolioInput | dict = None, horizon_days: int = 1, conf: float = 0.99, method: str = 'param') -> dict:
    """
    Calculate Volatility, Value at Risk (VaR), and Expected Shortfall (ES) for portfolio.
    
    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
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
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return {"error": str(e)}
    
    try:
        # Get portfolio returns using the utility
        portfolio_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=252,
            use_total_returns=False,  # Use price returns for volatility metrics
            dropna=True
        )
        
        if portfolio_returns is None or portfolio_returns.empty:
            return {"error": "No price data available for portfolio tickers"}

        # Calculate VaR/ES and volatility using calculations_v2
        if method == 'param':
            annual_vol = RiskCalculator.annualized_volatility(portfolio_returns)
            var_1day = RiskCalculator.parametric_var(annual_vol, confidence=conf)
            es_value = RiskCalculator.parametric_cvar(annual_vol, confidence=conf)

        elif method == 'hist':
            var_1day = RiskCalculator.historical_var(portfolio_returns, confidence=conf)
            es_value = RiskCalculator.expected_shortfall(portfolio_returns, confidence=conf)
            annual_vol = RiskCalculator.annualized_volatility(portfolio_returns)
            
        elif method == 'ewma':
            return {"error": "Method 'ewma' not supported with calculations_v2. Use 'param' or 'hist'."}
        else:
            return {"error": f"Invalid method '{method}'. Use 'param' or 'hist'"}

        # Scale VaR for time horizon and annualize
        var_scaled = float(var_1day) * np.sqrt(horizon_days)
        es_scaled = float(es_value) * np.sqrt(horizon_days)
        var_annual = float(var_1day) * np.sqrt(252)

        result = {
            'method': method,
            'confidence_level': conf,
            'horizon_days': horizon_days,
            'VaR': round(float(var_scaled), 6),
            'ES': round(float(es_scaled), 6),
            'vol': round(float(annual_vol), 6),
            'var_1day': round(float(var_1day), 6),
            'var_annual': round(float(var_annual), 6)
        }

        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate vol_es: {str(e)}"}


def risk_contribution(portfolio_dict: PortfolioInput | dict = None, metric: str = 'vol') -> dict:
    """
    Calculate Total Risk and risk contributions by asset.
    
    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    - metric: Risk metric to decompose {'vol', 'var'}
    
    Returns:
    - TR: Total Risk (portfolio level)
    - MCTR: Marginal Contribution to Total Risk (per asset)
    - CTR_pct: Component Total Risk as percentage (per asset)
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return {"error": str(e)}

    # Get tickers and weights from portfolio
    tickers = list(portfolio_dict.keys())
    weights_series = pd.Series({
        ticker: portfolio_dict[ticker]['allocation'] * (1 if portfolio_dict[ticker]['position'] == 'long' else -1)
        for ticker in tickers
    })
    
    try:
        # Get portfolio data using utility
        weights_dict, price_data, _ = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=252,
            include_dividends=False
        )
        
        if not price_data:
            return {"error": "No price data available for portfolio tickers"}
        
        # Calculate returns for each ticker
        returns_df = pd.DataFrame({
            ticker: ReturnsCalculator.daily_price_returns(prices)
            for ticker, prices in price_data.items()
            if prices is not None and not prices.empty
        }).dropna()
        
        if returns_df.empty:
            return {"error": "No price data available for portfolio tickers"}
        
        # Calculate covariance matrix using v2
        cov_matrix = RiskCalculator.covariance_matrix(returns_df, annualize=False)

        # Align weights to covariance columns
        aligned_weights = weights_series.reindex(cov_matrix.columns).fillna(0.0)
        w = aligned_weights.to_numpy(dtype=float)
        Sigma = cov_matrix.to_numpy(dtype=float)

        if metric == 'vol':
            # Volatility-based risk contribution
            portfolio_variance = float(w @ Sigma @ w)
            total_risk = float(np.sqrt(max(portfolio_variance, 0.0)))  # Portfolio volatility
            if total_risk == 0.0:
                marginal_contrib = np.zeros_like(w)
                component_contrib = np.zeros_like(w)
                ctr_pct = np.zeros_like(w)
            else:
                marginal_contrib = (Sigma @ w) / total_risk
                component_contrib = w * marginal_contrib
                ctr_pct = (component_contrib / total_risk) * 100.0

        elif metric == 'var':
            # VaR-based risk contribution using v2 marginal_var
            mv_series, cv_series = RiskCalculator.marginal_var(aligned_weights, cov_matrix, confidence=0.99, as_percent_of_portfolio_var=False)
            total_risk = float(cv_series.sum())
            marginal_contrib = mv_series.reindex(cov_matrix.columns).to_numpy(dtype=float)
            component_contrib = cv_series.reindex(cov_matrix.columns).to_numpy(dtype=float)
            if total_risk != 0.0:
                ctr_pct = (component_contrib / total_risk) * 100.0
            else:
                ctr_pct = np.zeros_like(component_contrib)

        else:
            return {"error": f"Invalid metric '{metric}'. Use 'vol' or 'var'"}
        
        # Build result dictionary
        result = {
            'metric': metric,
            'TR': round(float(total_risk), 6),
            'MCTR': {ticker: round(float(marginal_contrib[i]), 6) for i, ticker in enumerate(cov_matrix.columns)},
            'CTR_pct': {ticker: round(float(ctr_pct[i]), 2) for i, ticker in enumerate(cov_matrix.columns)}
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate risk_contribution: {str(e)}"}


def drawdown_profile(portfolio_dict: PortfolioInput | dict = None) -> dict:
    """
    Analyze portfolio drawdown characteristics.
    
    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    
    Returns:
    - max_dd: Maximum drawdown (worst peak-to-trough decline)
    - avg_dd: Average drawdown across all episodes  
    - ulcer: Ulcer Index (measure of drawdown severity and duration)
    - episodes: List of drawdown episodes with start/end dates and recovery times
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return {"error": str(e)}
    
    try:
        # Get portfolio returns using the utility for last 2 years
        portfolio_returns, weights = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=504,  # 2 years for better drawdown analysis
            use_total_returns=False,  # Use price returns for drawdown analysis
            dropna=True
        )
        
        if portfolio_returns is None or portfolio_returns.empty:
            return {"error": "No price data available"}
        
        # Calculate cumulative portfolio value (NAV)
        portfolio_nav = (1 + portfolio_returns).cumprod()

        # Calculate running maximum (peak values)
        running_max = portfolio_nav.expanding().max()

        # Calculate drawdown series
        drawdown = (portfolio_nav - running_max) / running_max

        # Calculate key metrics using v2 for max drawdown and ulcer index
        max_drawdown = float(RiskCalculator.max_drawdown(portfolio_nav))
        
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
        
        # Calculate Ulcer Index (RMS of drawdowns) via v2
        ulcer_index = float(RiskCalculator.ulcer_index(portfolio_nav))
        
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



