from backend.src.db.core.db_config import ProphitAltsSession, MarketSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.calculations_v2.portfolio.concentration import PortfolioConcentration
from datetime import datetime, timedelta
from typing import Dict
import pandas as pd
import warnings

from backend.src.calculations_v2.core import DataService
from backend.src.calculations_v2.returns import PortfolioReturnsCalculator, ReturnsCalculator
from backend.src.calculations_v2.risk import RiskCalculator

def get_analyst_picks(fund_name: str):
    session = ProphitAltsSession()
    initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == fund_name).all()

    initial_positions_dict = {}
    for position in initial_positions:
        initial_positions_dict[position.ticker_name] = {
            "position": position.position.value,
            "industry": position.industry,
            "conviction": position.conviction,
            "reasoning": position.reasoning
        }

    return initial_positions_dict

def exposure_calculator(portfolio_dict: dict, exposure_type: str):
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

def industry_concentration(portfolio_dict: dict, industry_level: str):
    if industry_level == "industry":
        res = PortfolioConcentration(portfolio_dict).industry_concentration()
    elif industry_level == "sub_industry":
        res = PortfolioConcentration(portfolio_dict).sub_industry_concentration()
    else:
        raise ValueError(f"Invalid industry level: {industry_level}")
    # Round values to 5 decimals for cleaner display
    return {k: round(float(v), 5) for k, v in res.items()}

def VaR_calculator(portfolio_dict: dict, level: str):
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


def calculate_portfolio_beta_vs_spy(
    portfolio_dict: Dict[str, Dict], 
    lookback_days: int = 252
) -> float:
    """
    Calculate CAPM beta for a long/short portfolio vs SPY.
    
    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use
    
    Returns:
        Portfolio beta vs SPY
    """
    # Extract weights from portfolio dict, applying sign based on position
    portfolio_weights = {}
    for ticker, config in portfolio_dict.items():
        allocation = config.get('allocation', 0.0)
        position = config.get('position', 'long')
        # Apply negative sign for short positions
        weight = -allocation if position == 'short' else allocation
        portfolio_weights[ticker] = weight
    
    # Fetch price data
    ds = DataService()
    tickers = list(portfolio_weights.keys()) + ['SPY']
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 50)  # Buffer for returns calc
    
    price_data = ds.get_bulk_close_series(tickers, start_date, end_date)
    
    # Calculate daily returns for each asset
    ticker_returns = {
        ticker: ReturnsCalculator.daily_price_returns(prices)
        for ticker, prices in price_data.items()
        if ticker != 'SPY' and prices is not None and not prices.empty
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
    
    # Get SPY returns
    spy_series = price_data.get('SPY')
    if spy_series is None or spy_series.empty:
        # Fallback fetch for SPY if not included in bulk result
        spy_pd = ds.get_price_data('SPY', start_date, end_date)
        spy_series = spy_pd.frame['close'] if spy_pd and spy_pd.frame is not None and not spy_pd.frame.empty else None
    if spy_series is None or spy_series.empty:
        return float('nan')
    spy_returns = ReturnsCalculator.daily_price_returns(spy_series)
    if spy_returns is None or spy_returns.empty:
        return float('nan')
    
    # Calculate and return beta
    return RiskCalculator.beta(portfolio_returns, spy_returns)



if __name__ == "__main__":
    # Suppress noisy runtime warnings from downstream covariance ops in CLI usage
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    portfolio_dict = {
        # Long positions
        "CL": {"allocation": 0.015, "position": "long"},
        "PM": {"allocation": 0.07, "position": "long"},
        "KO": {"allocation": 0.01, "position": "long"},
        "WMT": {"allocation": 0.045, "position": "long"},
        "BJ": {"allocation": 0.052, "position": "long"},
        "MNST": {"allocation": 0.05, "position": "long"},
        "INGR": {"allocation": 0.007, "position": "long"},
        "ODC": {"allocation": 0.07, "position": "long"},
        "CASY": {"allocation": 0.045, "position": "long"},
        "SFM": {"allocation": 0.01, "position": "long"},
        "VITL": {"allocation": 0.035, "position": "long"},
        "DOLE": {"allocation": 0.018, "position": "long"},
        "PPC": {"allocation": 0.025, "position": "long"},   
        "COCO": {"allocation": 0.03, "position": "long"},
        "CELH": {"allocation": 0.027, "position": "long"},
        "IPAR": {"allocation": 0.01, "position": "long"},
        "TPB": {"allocation": 0.02, "position": "long"},
        "ODD": {"allocation": 0.017, "position": "long"},
        "CENT": {"allocation": 0.012, "position": "long"},
        "CHEF": {"allocation": 0.01, "position": "long"},
        
        # Short positions (negative weights)
        "COTY": {"allocation": 0.03, "position": "short"},
        "SPB": {"allocation": 0.03, "position": "short"},
        "TGT": {"allocation": 0.015, "position": "short"},
        "ENR": {"allocation": 0.015, "position": "short"},
        "PEP": {"allocation": 0.02, "position": "short"},
        "KVUE": {"allocation": 0.015, "position": "short"},
        "KLG": {"allocation": 0.015, "position": "short"},
        "JJSF": {"allocation": 0.02, "position": "short"},
        "MGPI": {"allocation": 0.01, "position": "short"},
        "STZ": {"allocation": 0.01, "position": "short"},
        "WBA": {"allocation": 0.025, "position": "short"},
        "ANDE": {"allocation": 0.03, "position": "short"},
        "FRPT": {"allocation": 0.015, "position": "short"},
        "CPB": {"allocation": 0.02, "position": "short"},
    }

    print(exposure_calculator(portfolio_dict, "net"))
    print(exposure_calculator(portfolio_dict, "gross"))
    print(exposure_calculator(portfolio_dict, "long"))
    print(exposure_calculator(portfolio_dict, "short"))
    print(industry_concentration(portfolio_dict, "industry"))
    print(industry_concentration(portfolio_dict, "sub_industry"))
    print(VaR_calculator(portfolio_dict, "industry"))
    print(VaR_calculator(portfolio_dict, "sub_industry"))
    print(VaR_calculator(portfolio_dict, "portfolio"))
    print(calculate_portfolio_beta_vs_spy(portfolio_dict))