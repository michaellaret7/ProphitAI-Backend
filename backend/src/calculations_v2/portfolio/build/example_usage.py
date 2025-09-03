"""
Example usage of the CorrelationPortfolioBuilder.

This script demonstrates how to use the portfolio builder to create
an optimized portfolio using the calculations_v2 framework.
"""

from datetime import datetime
from backend.src.calculations_v2.core import DataService
from backend.src.calculations_v2.portfolio.build import CorrelationPortfolioBuilder
from backend.src.calculations_v2.core.config import DEFAULT_TRADING_DAYS


def basic_portfolio_example():
    """Basic example: Build a long-only portfolio with leverage."""
    
    # Initialize the builder (optionally with custom DataService)
    data_service = DataService()
    builder = CorrelationPortfolioBuilder(data_service)
    
    # Define portfolio parameters with conviction and position
    # Conviction is decimal allocation (0.25 = 25% of risk budget)
    tickers = {
        "AAPL": {"conviction": 0.25, "position": "long"},  # 25% allocation
        "MSFT": {"conviction": 0.20, "position": "long"},  # 20% allocation
        "GOOGL": {"conviction": 0.15, "position": "long"}, # 15% allocation
        "AMZN": {"conviction": 0.25, "position": "long"},  # 25% allocation
        "META": {"conviction": 0.15, "position": "long"}   # 15% allocation
    }
    
    target_annual_vol = 0.15  # 15% target volatility
    portfolio_value = 100000  # $100k portfolio
    leverage = 1.5  # 150% gross exposure
    
    # Build the portfolio
    result = builder.build_portfolio(
        tickers=tickers,
        target_annual_vol=target_annual_vol,
        portfolio_value=portfolio_value,
        leverage=leverage,
        lookback_days=DEFAULT_TRADING_DAYS  # 1 year of data
    )
    
    # Check results
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print("Portfolio Build Successful!")
    print(f"Status: {result['status']}")
    print(f"\nPortfolio Weights:")
    for ticker, weight in result['weights'].items():
        print(f"  {ticker}: {weight:.2%}")
    
    print(f"\nPosition Sizes:")
    for ticker, size in result['position_sizes'].items():
        print(f"  {ticker}: ${size:,.2f}")
    
    print(f"\nRisk Metrics:")
    metrics = result['risk_metrics']
    print(f"  Annual Volatility: {metrics.get('annual_volatility', 0):.2%}")
    print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
    print(f"  VaR (99%): {metrics.get('var_99', 0):.2%}")
    print(f"  Diversification Ratio: {metrics.get('diversification_ratio', 0):.2f}")
    
    print(f"\nExposure Metrics:")
    print(f"  Leverage: {result.get('leverage', 1):.1f}x")
    print(f"  Gross Exposure: {result.get('gross_exposure', 0):.1%}")
    print(f"  Net Exposure: {result.get('actual_net_exposure', 0):.1%}")
    print(f"  Long Exposure: {result.get('long_exposure', 0):.1%}")
    print(f"  Short Exposure: {result.get('short_exposure', 0):.1%}")

def long_short_portfolio_example():
    """Example: Long/short portfolio with target net exposure."""
    
    builder = CorrelationPortfolioBuilder()

    tickers = {
        # Long positions (convictions sum to ~1.0 within longs)
        "AAPL": {"conviction": 0.30, "position": "long"},   # 30% of long allocation
        "MSFT": {"conviction": 0.25, "position": "long"},   # 25% of long allocation
        "GOOGL": {"conviction": 0.20, "position": "long"},  # 20% of long allocation
        "NVDA": {"conviction": 0.25, "position": "long"},   # 25% of long allocation
        # Short positions (convictions sum to ~1.0 within shorts)
        "TSLA": {"conviction": 0.30, "position": "short"},  # 30% of short allocation
        "META": {"conviction": 0.40, "position": "short"},  # 40% of short allocation
        "NFLX": {"conviction": 0.30, "position": "short"}   # 30% of short allocation
    }
    
    # Build portfolio with specific net exposure
    result = builder.build_portfolio(
        tickers=tickers,
        target_annual_vol=0.12,  # 12% target vol
        portfolio_value=250000,  # $250k
        leverage=2.0,  # 200% gross exposure
        target_net_exposure=0.30,  # 30% net long
        max_position_weight=0.15
    )
    
    if "error" not in result:
        print("Long/Short Portfolio with Target Net Exposure")
        print("="*50)
        print(f"Target Net Exposure: {result['target_net_exposure']:.1%}")
        print(f"Actual Net Exposure: {result['actual_net_exposure']:.1%}")
        print(f"Gross Exposure: {result['gross_exposure']:.1%}")
        print(f"Leverage: {result['leverage']:.1f}x")
        
        print("\nPositions:")
        for ticker, weight in result['weights'].items():
            size = result['position_sizes'][ticker]
            position_type = "LONG" if weight > 0 else "SHORT"
            print(f"  {ticker:6} [{position_type:5}]: {abs(weight):5.1%} = ${abs(size):10,.0f}")
        
        print(f"\nRisk Metrics:")
        metrics = result['risk_metrics']
        print(f"  Annual Vol: {metrics.get('annual_volatility', 0):.1%}")
        print(f"  Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  VaR 99%: {metrics.get('var_99', 0):.2%}")


if __name__ == "__main__":
    print("="*60)
    print("CORRELATION PORTFOLIO BUILDER - USAGE EXAMPLES")
    print("="*60)
    
    # Run examples
    print("\n1. BASIC PORTFOLIO EXAMPLE (LONG-ONLY WITH LEVERAGE)")
    print("-"*40)
    basic_portfolio_example()
    
    print("\n\n2. LONG/SHORT PORTFOLIO WITH NET EXPOSURE")
    print("-"*40)
    long_short_portfolio_example()
    

