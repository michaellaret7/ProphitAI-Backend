"""Test script for async parallel tool execution.

Tests the parallel tool call functionality by running an agent with 4 ticker tools
and a prompt designed to trigger parallel execution.
"""

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.technicals import TECHNICALS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.weekly_returns import GET_WEEKLY_RETURNS_TOOL
from app.core.agentic_framework.base_agent.utils.models import PrintMode


def register_ticker_tools(agent: BaseAgent) -> None:
    """Register all 4 ticker tools with the agent."""
    tools = [
        CALCULATE_TICKER_FACTORS_TOOL,
        GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
        TECHNICALS_TOOL,
        GET_WEEKLY_RETURNS_TOOL,
    ]
    for tool in tools:
        agent.add_tool(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            function=tool["function"],
        )


def main():
    system_prompt = """You are a financial analyst assistant that analyzes stocks using available tools.

CRITICAL PLANNING CONSTRAINT: Your plan MUST have exactly 2 main tasks maximum:
1. Task 1: Gather data for all tickers (call tools in parallel for efficiency)
2. Task 2: Summarize findings and finalize

When gathering data, call multiple tools simultaneously for different tickers to maximize efficiency.
For example, if analyzing AAPL and MSFT, call get_ticker_performance_and_risk for both in the same turn.
"""

    user_prompt = """Analyze the performance metrics for these 4 tickers: AAPL, MSFT, GOOGL, NVDA.

For each ticker, get their core performance and risk metrics (use filters=['core'] for efficiency).

After gathering all data, provide a brief comparison summary ranking them by Sharpe ratio.

Remember: Maximum 2 main tasks in your plan. Call tools in parallel when possible."""

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_iterations=10,
        plan_first=True,
        print_mode=PrintMode.DEBUG,
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        temperature=0.7
    )

    register_ticker_tools(agent)

    result = agent.run()

    print("\n" + "=" * 60)
    print("FINAL RESULT:")
    print("=" * 60)
    print(f"Stop reason: {result['stop_reason']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Final answer: {result['final_answer']}")


if __name__ == "__main__":
    main()
