"""
Modular tool error testing with agent workflow observation.

This module provides a reusable function to test any tool with an agent,
triggering intentional errors and observing how the agent recovers.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.tests.tool_error_handling.tool_loader import load_tool_by_name
from app.core.agentic_framework.tests.tool_error_handling.test_scenarios import (
    get_scenarios_for_tool,
    get_portfolio_tool_scenarios,
    get_ticker_factor_scenarios,
    TOOL_SCENARIOS
)

def generate_test_prompt(tool_name: str, error_scenarios: List[str]) -> str:
    """
    Generate a test prompt for the agent with specified error scenarios.

    Args:
        tool_name: Name of the tool to test
        error_scenarios: List of error scenario descriptions

    Returns:
        Formatted prompt string for the agent

    Example:
        prompt = generate_test_prompt(
            "calculate_portfolio_performance",
            [
                "Pass portfolio_dict as string instead of dict",
                "Omit the required portfolio_dict parameter",
                "Call correctly with valid portfolio_dict"
            ]
        )
    """
    # Build numbered scenario list
    scenario_text = "\n".join([
        f"        {i+1}. {scenario}"
        for i, scenario in enumerate(error_scenarios)
    ])

    prompt = f"""
        Call the {tool_name} tool with the following test scenarios to observe error handling:
{scenario_text}
        {len(error_scenarios)+1}. After completing all tests, provide a final answer summarizing what you learned.

        After each error, carefully observe the error message and try to correct based on what it tells you.

        DO NOT CREATE A PLAN FOR THIS TEST.
        DO NOT USE ANY TASK MANAGEMENT TOOLS.
        """

    return prompt


def test_tool_with_agent(
    tool_name: str,
    error_scenarios: List[str],
    model: str = "gpt-4.1",
    max_iterations: int = 15,
    simulation_mode: bool = True,
    simulation_date: datetime = datetime(2024, 9, 30),
    # simulation_date: None = None,
    verbose: bool = True
) -> str:
    """
    Test a tool with an agent, triggering errors and observing recovery.

    Args:
        tool_name: Name of the tool to test (e.g., "calculate_portfolio_performance")
        error_scenarios: List of error scenario descriptions to test
        model: LLM model to use (default: "gpt-4o-mini")
        max_iterations: Maximum iterations for agent (default: 15)
        simulation_mode: If True, use simulation_date; if False, use production (None) (default: True)
        simulation_date: Date for simulation mode (default: 2024-09-30, ignored if simulation_mode=False)
        verbose: Print detailed agent execution logs (default: True)

    Returns:
        Final agent result/answer

    Example:
        # Test in simulation mode (with historical data cutoff)
        result = test_tool_with_agent(
            tool_name="calculate_portfolio_performance",
            error_scenarios=[...],
            simulation_mode=True,
            simulation_date=datetime(2024, 9, 30)
        )

        # Test in production mode (with live data)
        result = test_tool_with_agent(
            tool_name="calculate_portfolio_performance",
            error_scenarios=[...],
            simulation_mode=False
        )
    """
    # Determine simulation date based on mode
    agent_simulation_date = simulation_date if simulation_mode else None
    mode_label = "SIMULATION" if simulation_mode else "PRODUCTION"

    # Load the tool dynamically
    print(f"\n{'='*80}")
    print(f"LOADING TOOL: {tool_name}")
    print(f"{'='*80}\n")

    try:
        tool_def = load_tool_by_name(tool_name)
        print(f"✓ Tool loaded successfully")
        print(f"  Description: {tool_def['description'][:100]}...")
        print(f"  Parameters: {list(tool_def['parameters'].get('properties', {}).keys())}")
    except Exception as e:
        print(f"✗ Failed to load tool: {e}")
        return None

    # Generate test prompt
    user_prompt = generate_test_prompt(tool_name, error_scenarios)

    # Initialize agent
    print(f"\n{'='*80}")
    print(f"INITIALIZING AGENT")
    print(f"{'='*80}\n")
    print(f"Mode: {mode_label}")
    if simulation_mode and agent_simulation_date:
        print(f"Simulation date: {agent_simulation_date.date()}")
    elif not simulation_mode:
        print(f"Using live/production data (no date cutoff)")
    print(f"Model: {model}")
    print(f"Max iterations: {max_iterations}")
    print(f"Test scenarios: {len(error_scenarios)}")

    agent = BaseAgent(
        system_prompt=f"You are testing the error handling of the {tool_name} tool. Execute each test scenario carefully and observe the error messages.",
        user_prompt=user_prompt,
        model=model,
        max_iterations=max_iterations,
        use_error_memory=False,
        use_episodic_memory=False,
        verbose=verbose,
        plan_first=False,
        final_keywords=["Final Answer:", "FINAL ANSWER:"],
        save_messages=False,
        simulation_date=agent_simulation_date
    )

    # Register the tool
    agent.add_tool(**tool_def)
    print(f"\n✓ Tool registered with agent")

    # Run the test
    print(f"\n{'='*80}")
    print(f"RUNNING AGENT ERROR WORKFLOW TEST")
    print(f"{'='*80}\n")

    result = agent.run()

    # Print summary
    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print(f"\nFinal Result:\n{result}\n")

    return result


if __name__ == "__main__":
    """Example usage of the modular test function with scenario library."""

    print("="*80)
    print("SIMULATION DATA LEAKAGE FIX - TOOL TESTING")
    print("="*80)
    print("Testing tools that were recently fixed for simulation date filtering\n")


    # result1 = test_tool_with_agent(
    #     tool_name="get_ticker_fundamental_data",
    #     error_scenarios=get_scenarios_for_tool("get_ticker_fundamental_data"),
    #     simulation_mode=True,
    #     simulation_date=datetime(2024, 9, 30),
    #     max_iterations=15
    # )

    # result2 = test_tool_with_agent(
    #     tool_name="calculate_ticker_factors",
    #     error_scenarios=get_scenarios_for_tool("calculate_ticker_factors"),
    #     simulation_mode=True,
    #     simulation_date=datetime(2024, 9, 30),
    #     max_iterations=15
    # )

    # result3 = test_tool_with_agent(
    #     tool_name="get_industry_benchmark_calculations",
    #     error_scenarios=get_scenarios_for_tool("get_industry_benchmark_calculations"),
    #     simulation_mode=True,
    #     simulation_date=datetime(2024, 9, 30),
    #     max_iterations=15
    # )

    result4 = test_tool_with_agent(
        tool_name="get_sub_industry_benchmark_calculations",
        error_scenarios=get_scenarios_for_tool("get_sub_industry_benchmark_calculations"),
        simulation_mode=True,
        simulation_date=datetime(2024, 9, 30),
        max_iterations=15
    )

    result5 = test_tool_with_agent(
        tool_name="calculate_portfolio_performance",
        error_scenarios=get_scenarios_for_tool("calculate_portfolio_performance"),
        simulation_mode=True,
        simulation_date=datetime(2024, 9, 30),
        max_iterations=15
    )

    print("\n" + "="*80)
    print("All test scenarios configured!")
    print("Uncomment the test you want to run above")
    print("="*80)
