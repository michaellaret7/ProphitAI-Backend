"""Test for BaseAgentV2 - Medium complexity financial analysis task.

This test creates a financial analysis agent using BaseAgentV2 with REAL tools
from the tool_lib to test the V2 workflow.
"""

from app.core.agentic_framework.base_agent_v2 import BaseAgentV2
from pathlib import Path
import json

# Import real tool registrations
from app.domain.portfolio_operations.optimizer.tool_registry import register_optimizer_tools
from typing import Dict


class TestFinancialAgentV2(BaseAgentV2):
    """Test financial analysis agent using BaseAgentV2 with real tools."""

    def __init__(self, max_iterations: int = 50):
        """
        Initialize test financial agent.

        Args:
            max_iterations: Max iterations
        """
        # Build system prompt
        system_prompt = """
You are a senior equity research analyst at a long-only growth fund.

CRITICAL RULES:
1. You are FULLY AUTONOMOUS - make all decisions independently
2. NEVER ask the user questions - you cannot receive answers
3. NEVER say "shall I proceed" or "do you want me to" - just act
4. Use available tools to gather data and make evidence-based recommendations
5. Work efficiently - favor speed and decisiveness over exhaustive analysis
6. When a task/subtask is done, advance immediately using the appropriate tool
"""

        user_prompt = """
Identify investment opportunities in the stock market from the following group of tickers: AAPL, NVDA, TSLA, MSFT, AMZN, META.

REQUIREMENTS:
- Focus on QUALITY: strong balance sheets, positive free cash flow, sustainable margins
- Focus on GROWTH: revenue growth >10% annually, expanding market share or new products
- Focus on REASONABLE VALUATIONS: P/E under 30, or justified by growth prospects
- Consider both traditional OEMs and EV specialists
- Prioritize large-cap and mid-cap stocks (avoid micro-caps)
- Geographic focus: US-listed stocks with global or US/China exposure preferred

DELIVERABLE:
Provide exactly 2 stock picks with:
1. Ticker symbol and company name
2. 3-4 sentence investment thesis (why buy now)
3. Key metrics: Market cap, P/E, revenue growth, margins, cash position
4. Main risks (2-3 bullet points)
5. Suggested position size (% of portfolio)

Work efficiently. Quality analysis over exhaustive research.
"""

        # Initialize BaseAgentV2
        super().__init__(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="gpt-5-mini",
            reasoning_effort="low",
            max_iterations=25,  # Force faster decisions
            verbose=True,
            save_messages=True,
            use_episodic_memory=False
        )

    def run(self):
        """Override run to register industry tools before execution."""
        # Register real industry analysis tools
        if self.verbose:
            print("\nRegistering real financial analysis tools...")

        # Register optimizer tools (stock screener, fundamentals, factors, performance, etc.)
        register_optimizer_tools(self)

        if self.verbose:
            print(f"  Registered {len(self.tools)} total tools (including base tools)")

        return super().run()

def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_results(result: Dict):
    """Print test results."""
    print_section("TEST RESULTS")

    print(f"Success: {result.get('success')}")
    print(f"Iterations: {result.get('iterations')}")
    print(f"Reasoning Density: {result.get('reasoning_density_percentage')}%")
    print(f"Target: 30-40%")

    breakdown = result.get('breakdown', {})
    print(f"\nIteration Breakdown:")
    print(f"  - Thinking: {breakdown.get('thinking', 0)}")
    print(f"  - Action (tools): {breakdown.get('action', 0)}")
    print(f"  - Observation: {breakdown.get('observation', 0)}")
    print(f"  - Reasoning: {breakdown.get('reasoning', 0)}")

    if result.get('final_answer'):
        print(f"\nFinal Answer Provided: YES")
        print(f"\nFinal Answer:")
        print(f"{result['final_answer']}")
    else:
        print(f"\nFinal Answer Provided: NO")
        if result.get('error'):
            print(f"Error: {result['error']}")

    # Check task state
    task_state = result.get('task_state', {})
    if task_state:
        todo_list = task_state.get('todo_list', {})
        tasks = todo_list.get('tasks', [])
        print(f"\nPlan executed:")
        print(f"  - Total tasks: {len(tasks)}")
        completed = sum(1 for t in tasks if t.get('status') == 'completed')
        print(f"  - Completed: {completed}/{len(tasks)}")


def run_test():
    """Run medium complexity financial analysis test."""

    print("=" * 80)
    print("  BASE AGENT V2 - MEDIUM COMPLEXITY TEST")
    print("  Using REAL tools from tool_lib")
    print("=" * 80)

    print("\nTask: Automobile sector stock selection")
    print("Expected tools: stock_screener, get_ticker_fundamental_data, calculate_ticker_factors")

    agent = TestFinancialAgentV2(max_iterations=40)

    try:
        result = agent.run()
        print_results(result)

        # Check output files created
        print("\n\nOutput files created:")
        output_dirs = sorted(Path("agent_output").glob("**/TestFinancialAgentV2_*"))
        if output_dirs:
            latest_dir = output_dirs[-1]
            print(f"\n  {latest_dir}:")
            files = sorted(latest_dir.glob("*.json"))
            for file in files:
                size_kb = file.stat().st_size / 1024
                print(f"    - {file.name} ({size_kb:.1f} KB)")

        return result

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    run_test()