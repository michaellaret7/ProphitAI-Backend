"""Simple Agent Test - Basic Functionality Example

This is a minimal test that demonstrates the agent's core capabilities
with a simple portfolio analysis task.
"""

from app.core.agentic_framework.base_agent_v2.agent import SimpleAgent
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode

# Import minimal tool set
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import (
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)


def register_simple_tools(agent: SimpleAgent) -> None:
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

    # Simple system prompt
    system_prompt = """
You are a portfolio analyst. Analyze portfolios using the available tools and provide clear insights.
"""

    # Simple task
    user_prompt = f"""Analyze this portfolio and tell me:
1. What are the portfolio's returns and risk metrics?
2. Which individual stock has performed best?

Portfolio: {sample_portfolio}
"""

    # Initialize agent with simple settings
    agent = SimpleAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",
        max_iterations=15,
        print_mode=PrintMode.DEBUG,
        plan_first=True,  # No planning for simple test
        reasoning_effort="high"
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
