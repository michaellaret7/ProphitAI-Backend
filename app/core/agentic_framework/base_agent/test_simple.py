"""Simple Agent Test - Edit Plan Tool Testing

This test demonstrates the edit_plan tool functionality by having the agent
create a simple plan and then modify it using various edit operations.

NOTE: edit_plan is now a base tool and is automatically registered with all agents.
"""

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode

# Import minimal tool set
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import (
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)


def register_simple_tools(agent: BaseAgent) -> None:
    """Register minimal tool set for simple test.

    Note: edit_plan is automatically registered as a base tool, no need to add it here.
    """
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
    You are a test agent for portfolio services.

    Portfolio:
    - AAPL: allocation 0.40, position long
    - MSFT: allocation 0.35, position long
    - NVDA: allocation 0.25, position long
    """

    user_prompt = """
    Your task is to analyze the portfolio and provide a comprehensive assessment and write many notes using the notes tool.
    Then you are supposed to use the retrieve_notes tool to retrieve the notes and use them to analyze the portfolio and provide a comprehensive assessment.
    """

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",
        # model="claude-sonnet-4-5-20250929",  # Use Sonnet for better reasoning
        model="claude-haiku-4-5-20251001",
        max_iterations=150,
        print_mode=PrintMode.DEBUG,
        plan_first=True  # Create plan first
    )

    # Register tools
    print("\n" + "="*80)
    print("EDIT_PLAN TOOL TEST - Dynamic Plan Modification")
    print("="*80)
    print("Testing: ADD, DROP, EDIT operations with automatic task renaming")
    print("="*80 + "\n")

    register_simple_tools(agent)

    # Run agent
    result = agent.run()

    return result


if __name__ == "__main__":
    main()
