"""Portfolio Analysis Agent - Complex Multi-Tool Example

This agent analyzes a portfolio to identify strengths/weaknesses and proposes
evidence-backed trade ideas using portfolio and ticker tools.
"""

from app.core.agentic_framework.base_agent_v2.agent import BaseAgent
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode
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
Role: You are a senior portfolio analyst with expertise in quantitative analysis and fundamental research.
Task: Your task is to perform a comprehensive portfolio analysis and provide actionable insights.
Rules: You are never allowed to skip any main or sub tasks. (there will be severe consequences if you do)

Your capabilities include:
- Portfolio-level analysis: returns, volatility, exposures, concentrations, correlations, beta
- Ticker-level analysis: performance metrics, risk-adjusted returns, factor exposures, fundamentals
- Risk assessment: VaR, correlations, industry concentrations
- Trade idea generation: evidence-backed recommendations
- Use the stock screener tool to find other stocks to help with your trade idea.
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
   - Based on your analysis, propose TWO-FOUR specific trade ideas
   - The trade should address a weakness OR capitalize on a strength
   - Back your recommendation with specific evidence from your analysis
   - Be specific: What to buy/sell, how much, and why

Output JSON Format:
{{
    "initial_portfolio": {{
        "TICKER": {{
            "allocation": 0.10,
            "position": "long"
        }}
    }},
    "final_portfolio": {{
        "TICKER": {{
            "allocation": 0.10,
            "position": "long"
        }}
    }},
    "changes": {{
        "added": {{
            "TICKER": "Reason for adding this ticker"
        }},
        "removed": {{
            "TICKER": "Reason for removing this ticker"
        }},
        "adjusted": {{
            "TICKER": "Reason for allocation adjustment"
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
        provider="anthropic",  # Use OpenAI
        # model="claude-haiku-4-5-20251001",
        model="claude-sonnet-4-5-20250929",  # Use GPT-4o for complex analysis
        max_iterations=100,  # Allow many iterations for thorough analysis
        print_mode=PrintMode.VERBOSE,
        plan_first=True,  # Create a plan before executing
        temperature=0.7,
        reasoning_effort="high",
        simulation_date=datetime(2024, 1, 1)
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
