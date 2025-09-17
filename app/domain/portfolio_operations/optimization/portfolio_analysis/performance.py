from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

# Define the user portfolio
long_only_portfolio = {
    "AAPL": {"position": "long", "allocation": 0.07},
    "MSFT": {"position": "long", "allocation": 0.07},
    "GOOGL": {"position": "long", "allocation": 0.06},
    "AMZN": {"position": "long", "allocation": 0.06},
    "NVDA": {"position": "long", "allocation": 0.06},
    "TSLA": {"position": "long", "allocation": 0.05},
    "JPM": {"position": "long", "allocation": 0.05},
    "V": {"position": "long", "allocation": 0.05},
    "JNJ": {"position": "long", "allocation": 0.05},
    "PG": {"position": "long", "allocation": 0.05},
    "XOM": {"position": "long", "allocation": 0.05},
    "UNH": {"position": "long", "allocation": 0.05},
    "HD": {"position": "long", "allocation": 0.05},
    "SPY": {"position": "long", "allocation": 0.06},
    "QQQ": {"position": "long", "allocation": 0.05},
    "IWM": {"position": "long", "allocation": 0.04},
    "EFA": {"position": "long", "allocation": 0.04},
    "EEM": {"position": "long", "allocation": 0.04},
}

long_short_portfolio = {
    "AAPL": {"position": "long", "allocation": 0.05},
    "MSFT": {"position": "long", "allocation": 0.05},
    "GOOGL": {"position": "long", "allocation": 0.05},
    "AMZN": {"position": "long", "allocation": 0.05},
    "NVDA": {"position": "long", "allocation": 0.05},
    "PG": {"position": "long", "allocation": 0.04},
    "JNJ": {"position": "long", "allocation": 0.04},
    "XOM": {"position": "long", "allocation": 0.04},
    "JPM": {"position": "long", "allocation": 0.04},
    "SPY": {"position": "long", "allocation": 0.05},
    
    "TSLA": {"position": "short", "allocation": 0.04},
    "NFLX": {"position": "short", "allocation": 0.04},
    "ZM": {"position": "short", "allocation": 0.03},
    "COIN": {"position": "short", "allocation": 0.03},
    "RIVN": {"position": "short", "allocation": 0.03},
    "MARA": {"position": "short", "allocation": 0.03},
    "GME": {"position": "short", "allocation": 0.03},
    "AMC": {"position": "short", "allocation": 0.03},
    "ARKK": {"position": "short", "allocation": 0.04},
    "IWM": {"position": "short", "allocation": 0.03},
    "EEM": {"position": "short", "allocation": 0.03},
    "BYND": {"position": "short", "allocation": 0.02}
}

etf_hedge_portfolio = {
    "JPM": {"position": "long", "allocation": 0.07},
    "BAC": {"position": "long", "allocation": 0.06},
    "MS": {"position": "long", "allocation": 0.06},
    "GS": {"position": "long", "allocation": 0.06},
    "WFC": {"position": "long", "allocation": 0.05},
    "C": {"position": "long", "allocation": 0.05},
    "PNC": {"position": "long", "allocation": 0.05},
    "SCHW": {"position": "long", "allocation": 0.05},
    "USB": {"position": "long", "allocation": 0.05},
    "BK": {"position": "long", "allocation": 0.05},

    "XLF": {"position": "short", "allocation": 0.20},
    "KBE": {"position": "short", "allocation": 0.10},
    "KRE": {"position": "short", "allocation": 0.10}
}

dividend_portfolio = {
    "VYM": {"position": "long", "allocation": 0.10},
    "SCHD": {"position": "long", "allocation": 0.10},
    "DVY": {"position": "long", "allocation": 0.08},
    "HDV": {"position": "long", "allocation": 0.08},
    "NOBL": {"position": "long", "allocation": 0.08},
    "SPYD": {"position": "long", "allocation": 0.08},
    "SDY": {"position": "long", "allocation": 0.08},
    "FDL": {"position": "long", "allocation": 0.08},
    "DHS": {"position": "long", "allocation": 0.08},
    "VIG": {"position": "long", "allocation": 0.08},
    "IDV": {"position": "long", "allocation": 0.08},
    "EFAD": {"position": "long", "allocation": 0.08}
}

def calculate_portfolio_performance(portfolio, lookback_days=252, use_total_returns=True):
    """Simple portfolio performance calculation using gross exposure.
    
    Args:
        portfolio: Dict of holdings with position and allocation
        lookback_days: Number of days to look back
        use_total_returns: If True, include dividends; if False, price-only returns
    """
    
    # Use the new utility function to get portfolio returns
    portfolio_returns, weights = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
        dropna=True,
        normalization="gross"
    )
    
    # Get benchmark returns
    benchmark_returns = get_benchmark_returns(
        benchmark="SPY",
        lookback_days=lookback_days,
        use_total_returns=use_total_returns
    )
    
    # Calculate capture ratios
    up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(
        portfolio_returns, benchmark_returns, periods_per_year=None
    )
    up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(
        portfolio_returns, benchmark_returns, periods_per_year=252
    )
    
    metrics = {
        # Core risk-adjusted metrics
        "sharpe": PerformanceCalculator.sharpe_ratio(portfolio_returns),
        "sortino": PerformanceCalculator.sortino_ratio(portfolio_returns),
        "treynor": PerformanceCalculator.treynor_ratio(portfolio_returns, benchmark_returns),
        "info": PerformanceCalculator.information_ratio(portfolio_returns, benchmark_returns),
        "alpha": PerformanceCalculator.alpha_jensen(portfolio_returns, benchmark_returns),
        
        # Advanced risk-adjusted metrics
        "omega": PerformanceCalculator.omega_ratio(portfolio_returns),
        "sterling": PerformanceCalculator.sterling_ratio_from_returns(portfolio_returns),
        "burke": PerformanceCalculator.burke_ratio(portfolio_returns),
        "martin": PerformanceCalculator.martin_ratio(portfolio_returns),
        
        # Capture ratios
        "up_cap_daily": up_cap_daily,
        "down_cap_daily": down_cap_daily,
        "up_cap_ann": up_cap_ann,
        "down_cap_ann": down_cap_ann,
        
        # Win/loss metrics
        "win_rate": PerformanceCalculator.win_rate(portfolio_returns),
        "pf_ret": PerformanceCalculator.profit_factor_from_returns(portfolio_returns),
        "pf_eq": PerformanceCalculator.profit_factor(portfolio_returns, start_equity=1.0),
        
        # Drawdown and pain metrics
        "pain": PerformanceCalculator.pain_index(portfolio_returns),
        "tail_ratio": PerformanceCalculator.tail_ratio(portfolio_returns, q=5.0),
        "gain_loss": PerformanceCalculator.gain_loss_ratio(portfolio_returns, threshold=0.0, method="mean"),
        "ulcer": PerformanceCalculator.ulcer_index(portfolio_returns, window=None, as_percent=False),
        "ulcer_252pct": PerformanceCalculator.ulcer_index(portfolio_returns, window=252, as_percent=True),
    }
    # Round numeric metrics to 4 decimals, keep non-finite and non-numeric as-is
    metrics = {
        key: (round(value, 4) if isinstance(value, (float, int, np.floating)) and np.isfinite(value) else value)
        for key, value in metrics.items()
    }
    
    return metrics, portfolio_returns


def calculate_simple_metrics(portfolio, lookback_days=252):
    """Calculate and display simple portfolio metrics.
    
    Returns:
        dict: Contains annualized returns, volatility, and weekly cumulative returns
    """
    # Get price-only returns
    portfolio_price_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=False,
        dropna=True
    )
    
    # Get total returns
    portfolio_total_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=True,
        dropna=True
    )
    
    # Calculate metrics
    ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
    ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
    ann_volatility = portfolio_total_returns.std() * np.sqrt(252)
    
    # Calculate weekly cumulative returns and convert to rounded dict
    weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
    weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}
    
    # Calculate cumulative return over period
    total_cumulative = (1 + portfolio_total_returns).prod() - 1
    
    return {
        "ann_price_return": round(ann_price_return, 4),
        "ann_total_return": round(ann_total_return, 4),
        "ann_volatility": round(ann_volatility, 4),
        "weekly_returns": weekly_returns,
        "cumulative_return": round(total_cumulative, 4)
    }


# Run the calculation
if __name__ == "__main__":
    # Calculate with total returns (includes dividends) by default
    lookback_days = 252 * 3  # 3 years
    metrics, returns = calculate_portfolio_performance(
        dividend_portfolio, 
        lookback_days=lookback_days,
        use_total_returns=True 
    )

    print(metrics)
    # Also calculate and display simple metrics
    simple_metrics = calculate_simple_metrics(dividend_portfolio, lookback_days)
    print(simple_metrics)