"""Simple Agent Test - Basic Functionality Example

This is a minimal test that demonstrates the agent's core capabilities
with a simple portfolio analysis task.
"""

from app.core.agentic_framework.base_agent_v2.agent import BaseAgent
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode

# Import minimal tool set
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import (
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)


def register_simple_tools(agent: BaseAgent) -> None:
    """Register minimal tool set for simple test."""
    tools = [
        CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
        GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
    ]

    for tool in tools:
        agent.add_tool(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            function=tool["function"]
        )


def main():
    """Run simple agent test with minimal portfolio."""

    # Simple 3-stock portfolio
    sample_portfolio = {
        "AAPL": {"allocation": 0.40, "position": "long"},
        "MSFT": {"allocation": 0.35, "position": "long"},
        "NVDA": {"allocation": 0.25, "position": "long"},
    }

    system_prompt = """
    You are a simple agent that will be used to test the agentic framework.
    Your task is to calculate the portfolio returns metrics for the following portfolio:
    # Example fake portfolio (3 stocks, realistic allocations)
    # (This will be echoed for the LLM. The actual data object is `sample_portfolio` in the code.)
    # AAPL: 40% (long), MSFT: 35% (long), NVDA: 25% (long)
    Portfolio:
    - AAPL: allocation 0.40, position long
    - MSFT: allocation 0.35, position long
    - NVDA: allocation 0.25, position long
    """
    user_prompt = "Calculate the portfolio returns metrics for the portfolio. All you have to do is calc the portfolio metrics, you don't need to do anything else. Keep the plan EXTREMELY short and concise."

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="openai",
        model="gpt-4.1",
        max_iterations=150,
        print_mode=PrintMode.DEBUG,
        plan_first=True,  # No planning for simple test
        # reasoning_effort="low"
    )

    # Register tools
    print("\n" + "="*80)
    print("SIMPLE AGENT TEST")
    print("="*80)

    register_simple_tools(agent)

    # Run agent
    result = agent.run()

    return result


if __name__ == "__main__":
    main()
