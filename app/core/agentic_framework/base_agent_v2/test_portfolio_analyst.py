"""Portfolio Analysis Agent - Complex Multi-Tool Example

This agent analyzes a portfolio to identify strengths/weaknesses and proposes
evidence-backed trade ideas using portfolio and ticker tools.
"""

from app.core.agentic_framework.base_agent_v2.agent import SimpleAgent
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode

# Import tool definitions from tool_lib
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL,
    INDUSTRY_CONCENTRATION_TOOL,
    VAR_CALCULATOR_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import (
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.beta import (
    CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.pairwise_corr_analysis import (
    PAIRWISE_CORR_ANALYSIS_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import (
    CALCULATE_TICKER_FACTORS_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import (
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
)


def register_portfolio_analysis_tools(agent: SimpleAgent) -> None:
    """Register all tools needed for portfolio analysis."""

    # Portfolio-level tools
    tools = [
        EXPOSURE_CALCULATOR_TOOL,
        INDUSTRY_CONCENTRATION_TOOL,
        VAR_CALCULATOR_TOOL,
        CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
        CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
        PAIRWISE_CORR_ANALYSIS_TOOL,

        # Ticker-level tools
        GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
        CALCULATE_TICKER_FACTORS_TOOL,
        GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    ]

    for tool in tools:
        agent.add_tool(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            function=tool["function"]
        )


def main():
    """Run portfolio analysis agent on a sample portfolio."""

    # Sample portfolio - Mix of strong performers and weak performers
    # This portfolio hasn't been rebalanced and shows both winners and losers
    sample_portfolio = {
        # Strong performers (AI/Tech winners)
        "NVDA": {"allocation": 0.15, "position": "long"},   # 15% Nvidia - AI chip leader
        "PLTR": {"allocation": 0.08, "position": "long"},   # 8% Palantir - AI/Data analytics
        "AVGO": {"allocation": 0.07, "position": "long"},   # 7% Broadcom - Semiconductors
        "HIMS": {"allocation": 0.06, "position": "long"},   # 6% Hims & Hers - Telehealth

        # Solid large caps (moderate performers)
        "AAPL": {"allocation": 0.12, "position": "long"},   # 12% Apple - Steady performer
        "MSFT": {"allocation": 0.12, "position": "long"},   # 12% Microsoft - AI exposure
        "JPM": {"allocation": 0.08, "position": "long"},    # 8% JPMorgan - Financials

        # Weak performers (losers needing review)
        "INTC": {"allocation": 0.10, "position": "long"},   # 10% Intel - Down 60% in 2024
        "WBA": {"allocation": 0.09, "position": "long"},    # 9% Walgreens - Down 64% in 2024
        "MRNA": {"allocation": 0.07, "position": "long"},   # 7% Moderna - Down 60%, post-COVID decline
        "EL": {"allocation": 0.04, "position": "long"},     # 4% Estée Lauder - China exposure issues
        "GLOB": {"allocation": 0.02, "position": "long"},   # 2% Globant - Down 57% in 2025
    }

    # System prompt - defines the agent's role and capabilities
    system_prompt = """
Role: You are a senior portfolio analyst with expertise in quantitative analysis and fundamental research.
Task: Your task is to perform a comprehensive portfolio analysis and provide actionable insights.

Your capabilities include:
- Portfolio-level analysis: returns, volatility, exposures, concentrations, correlations, beta
- Ticker-level analysis: performance metrics, risk-adjusted returns, factor exposures, fundamentals
- Risk assessment: VaR, correlations, industry concentrations
- Trade idea generation: evidence-backed recommendations
"""

    # User prompt - specific task with the portfolio
    user_prompt = f"""Analyze the following portfolio and provide a comprehensive assessment:

Portfolio:
{sample_portfolio}

Please perform the following analysis:

1. **Portfolio Overview**:
   - Calculate key metrics (returns, volatility, Sharpe ratio)
   - Assess portfolio beta vs SPY
   - Check exposure types and concentration risks

2. **Risk Analysis**:
   - Industry concentration analysis
   - Correlation analysis between holdings
   - Value at Risk (VaR) assessment

3. **Strengths & Weaknesses**:
   - Summarize portfolio strengths (what's working well)
   - Summarize portfolio weaknesses (areas of concern)

4. **Trade Idea**:
   - Based on your analysis, propose ONE specific trade idea
   - The trade should address a weakness OR capitalize on a strength
   - Back your recommendation with specific evidence from your analysis
   - Be specific: What to buy/sell, how much, and why

Take your time and be thorough. Use the available tools to gather evidence before making conclusions.
"""

    # Initialize agent
    agent = SimpleAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",  # Use OpenAI
        # model="gpt-5",  # Use GPT-4o for complex analysis
        max_iterations=60,  # Allow many iterations for thorough analysis
        print_mode=PrintMode.DEBUG,
        plan_first=True,  # Create a plan before executing
        reasoning_effort="high"
    )

    # Register analysis tools
    print("\n" + "="*80)
    print("REGISTERING PORTFOLIO ANALYSIS TOOLS")
    print("="*80)
    register_portfolio_analysis_tools(agent)

    # Run the agent
    print("\n" + "="*80)
    print("STARTING PORTFOLIO ANALYSIS")
    print("="*80)
    result = agent.run()


    return result


if __name__ == "__main__":
    main()
