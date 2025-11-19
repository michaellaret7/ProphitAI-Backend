"""Portfolio Analysis Agent - Complex Multi-Tool Example

This agent analyzes a portfolio to identify strengths/weaknesses and proposes
evidence-backed trade ideas using portfolio and ticker tools.
"""

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from datetime import datetime
import random

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
from app.core.agentic_framework.tool_lib.data_tools.stock_screener.tool import STOCK_SCREENER_TOOL

# Additional tools for portfolio creation and risk analysis
from app.core.agentic_framework.tool_lib.portfolio_tools.build_allocations import (
    BUILD_PORTFOLIO_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.asset_risk_contrib import (
    RISK_CONTRIBUTION_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.vol_es import (
    VOL_ES_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.stress_test import (
    STRESS_TEST_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import (
    FACTOR_TILTS_FOR_PORTFOLIO_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.cov_matrix import (
    CALCULATE_COVARIANCE_MATRIX_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import (
    CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import (
    CORRELATION_MATRIX_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.technicals import (
    TECHNICALS_TOOL,
)



def register_portfolio_analysis_tools(agent: BaseAgent) -> None:
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
        STOCK_SCREENER_TOOL,
        TECHNICALS_TOOL,

        # Portfolio construction & risk tools
        BUILD_PORTFOLIO_TOOL,
        RISK_CONTRIBUTION_TOOL,
        VOL_ES_TOOL,
        STRESS_TEST_TOOL,
        FACTOR_TILTS_FOR_PORTFOLIO_TOOL,
        CALCULATE_COVARIANCE_MATRIX_TOOL,
        CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
        CORRELATION_MATRIX_TOOL,
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

    # Build a random 15-position portfolio with 60% equities and 40% ETFs
    equity_candidates = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "IBM", "ORCL", "CSCO", "INTC", "JNJ",
        "MRK", "ABBV", "PG", "KO", "PEP", "WMT", "HD", "XOM", "CVX", "JPM", "BAC"
    ]
    etf_candidates = [
        "SPY", "VOO", "VTI", "IVV", "IWM", "EFA", "EEM", "AGG", "BND", "LQD",
        "HYG", "VNQ", "XLV", "XLF", "XLE", "XLU", "XLI", "XLY", "XLC", "XLB"
    ]
    excluded_high_growth = {"NVDA", "PLTR"}
    equity_pool = [t for t in equity_candidates if t not in excluded_high_growth]

    equities_count, etfs_count = 9, 6  # total 15 positions
    selected_equities = random.sample(equity_pool, equities_count)
    selected_etfs = random.sample(etf_candidates, etfs_count)

    def generate_weights(count, total):
        raw = [random.random() for _ in range(count)]
        s = sum(raw) or 1.0
        return [w / s * total for w in raw]

    equity_weights = generate_weights(equities_count, 0.60)
    etf_weights = generate_weights(etfs_count, 0.40)

    sample_portfolio = {}
    for ticker, w in zip(selected_equities, equity_weights):
        sample_portfolio[ticker] = {"allocation": round(w, 4), "position": "long"}
    for ticker, w in zip(selected_etfs, etf_weights):
        sample_portfolio[ticker] = {"allocation": round(w, 4), "position": "long"}

    # System prompt - defines the agent's role and capabilities
    system_prompt = """
Role: You are a senior portfolio manager with expertise in quantitative analysis and fundamental research.
Task: Your task is to construct a portfolio that is around 70% equities and 30% ETFs (DO NOT INCLUDE SPY).
Goal: The portfolio theme and goal should be to maximize returns while minimizing volatility, beta, and correlation. We want high growth and momentum balnced out by some etf lower volatility safer plays.
Rules: You are never allowed to skip any main or sub tasks. (there will be severe consequences if you do)

Your capabilities include:
- Portfolio-level analysis: returns, volatility, exposures, concentrations, correlations, beta
- Ticker-level analysis: performance metrics, risk-adjusted returns, factor exposures, fundamentals
- Risk assessment: VaR, correlations, industry concentrations
- Use the stock screener tool to find other stocks to help with your portfolio construction.
"""

    # User prompt - specific task with the portfolio
    user_prompt = f"""Construct a diversified low correlation long-only portfolio from scratch:

CRITICAL: This analysis is being conducted as of January 1, 2023 (simulation_date).
When using free_search for market research, ALWAYS include "as of January 2023" or "early 2023" in your queries.

Please perform the following tasks:

1. **Market Research & Economic Context**:
   - Use free_search to research macroeconomic conditions, sector outlooks, and market themes as of January 2023
   - CRITICAL: Include "as of January 2023" or "early 2023" in EVERY free_search query
   - Identify opportunities and risks based on early 2023 market conditions

2. **Define Portfolio Structure**:
   - Define target sector breakdown for equities (Technology, Healthcare, Financials, Consumer, Industrials, Energy, etc.)
   - Define ETF categories needed (core market, sector tilts, international, fixed income, etc.)
   - Specify diversification rules (sector limits, position limits, industry limits)
   - Justify structure based on 2023 market research

3. **Portfolio Objectives & Constraints**:
   - Target mix: 70% equities, 30% ETFs
   - Total positions: ~15
   - Exclude highly speculative names such as NVDA and PLTR
   - Aim for balanced sector and factor exposure per your defined structure

4. **Selection & Sizing**:
   - Use stock_screener and available tools to select equities and ETFs
   - Propose tickers and weights that sum to 1.0
   - Provide a brief rationale for each holding tied to your structure and 2023 research

5. **Risk & Diversification Checks**:
   - Report beta vs SPY, VaR, industry concentration, and pairwise correlations
   - Verify compliance with your defined diversification rules
   - Identify major risk contributors and concentration concerns

6. **Final Portfolio Proposal**:
   - Present the final portfolio with weights organized by sector
   - Summarize expected risk/return profile and key assumptions

Output JSON Format:
{{
    "final_portfolio": {{
        "TICKER": {{
            "allocation": 0.10,
            "position": "long"
        }}
    }}
}}

Take your time and be thorough. Use the available tools to gather evidence before making conclusions. Be concise in your final answer.

Rules:
- You are never allowed to skip any main or sub tasks. (there will be severe consequences if you do)
- You are never allowed to list all of the subtasks in a main task as in progress, the most subtasks that can be in progress at once is 2.
- You must review the Insights section before you start the workflow.
- Once you have your final answer and you are 100% sure about your final answer, call the finalize tool to deliver the final answer.
- You have the option to dynamically edit your plan using the edit_plan tool if you discover new tasks are needed, want to drop irrelevant tasks, or need to adjust task descriptions. This is completely optional - only use it if you genuinely need to adapt your plan based on new information or changing requirements.
"""

    # Initialize agent
    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        # provider="openai",
        # model="gpt-5-mini",
        provider="anthropic",  # Use OpenAI
        # model="claude-haiku-4-5-20251001",
        model="claude-sonnet-4-5-20250929", 
        max_iterations=150,  # Allow many iterations for thorough analysis
        print_mode=PrintMode.DEBUG,
        plan_first=True,  # Create a plan before executing
        # temperature=0.7,
        # reasoning_effort="medium",
        simulation_date=datetime(2023, 1, 1)
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
