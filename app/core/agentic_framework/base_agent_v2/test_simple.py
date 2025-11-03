"""Simple Agent Test - Edit Plan Tool Testing

This test demonstrates the edit_plan tool functionality by having the agent
create a simple plan and then modify it using various edit operations.

NOTE: edit_plan is now a base tool and is automatically registered with all agents.
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
    You are a test agent for demonstrating the edit_plan tool functionality.

    Portfolio:
    - AAPL: allocation 0.40, position long
    - MSFT: allocation 0.35, position long
    - NVDA: allocation 0.25, position long

    IMPORTANT: You have access to the edit_plan tool which allows you to modify your plan dynamically.
    """

    user_prompt = """Your task is to test the edit_plan tool with the following sequence:

1. First, create a SIMPLE 3-task plan (keep it minimal):
   - Task 1: Gather ticker performance data
   - Task 2: Calculate portfolio metrics
   - Task 3: Analyze results

2. After creating the plan, test the edit_plan tool by doing the following edits IN ORDER:

   a) ADD a new subtask "2b" at position 1 in Task 2 (parent_task_id="2")
      - Description: "Validate portfolio weights sum to 100%"
      - insert_position: 1
      - This should trigger automatic renaming of existing subtasks

   b) ADD a new main task "4" at the end
      - Description: "Generate summary report"
      - priority: 1

   c) DROP subtask "1a" (if Task 1 has subtasks)

   d) EDIT Task 3's description to "Analyze results and identify optimization opportunities"

3. After each edit operation, observe and report what happened to the plan structure.

Keep your plan EXTREMELY minimal with just 3 tasks total. Focus on testing the edit_plan tool properly."""

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",  # Use Sonnet for better reasoning
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
