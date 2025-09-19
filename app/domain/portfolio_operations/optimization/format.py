from app.core.calculations.portfolio.concentration import PortfolioConcentration
from app.core.agentic_framework.base_agent.tool_lib.portfolio.corr_matrix import correlation_matrix
from app.core.agentic_framework.base_agent.tool_lib.portfolio.performance import calculate_portfolio_performance
from app.core.agentic_framework.base_agent.tool_lib.portfolio.returns import calculate_portfolio_returns_metrics
from app.core.agentic_framework.base_agent.tool_lib.portfolio.ticker_performance import calculate_ticker_performances
from app.core.agentic_framework.base_agent.tool_lib.portfolio.group_performance import calculate_group_performances

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

def sector_concentration(portfolio_dict: dict):
    return {
        "industry": PortfolioConcentration(portfolio_dict).industry_concentration(),
        "sub_industry": PortfolioConcentration(portfolio_dict).sub_industry_concentration(),
        "sector": PortfolioConcentration(portfolio_dict).sector_concentration()
    }

def format_data(user_portfolio: dict):
    performance = calculate_portfolio_performance(user_portfolio)

    cm_df = correlation_matrix(user_portfolio)
    ticker_df = calculate_ticker_performances(user_portfolio)
    sector_df = calculate_group_performances(user_portfolio, group_by="sector")
    industry_df = calculate_group_performances(user_portfolio, group_by="industry")
    subindustry_df = calculate_group_performances(user_portfolio, group_by="sub_industry")

    payload = {
        "portfolio": user_portfolio,
        "sector_concentration": sector_concentration(user_portfolio),  # if DF: .round(4).to_dict("records")
        "correlation_matrix": cm_df,                                   # already formatted dict
        "portfolio_performance": performance,                # dict
        "portfolio_returns_metrics": calculate_portfolio_returns_metrics(user_portfolio),  # already dict
        "ticker_performances": ticker_df.round(4).to_dict("records"),
        "sector_performances": sector_df.round(4).to_dict("records"),
        "industry_performances": industry_df.round(4).to_dict("records"),
        "subindustry_performances": subindustry_df.round(4).to_dict("records"),
    }
    return payload
