"""Test: Agent with deferred tools — portfolio analysis + worker research."""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_tools.registry import ALL_TOOL_FUNCTIONS


def main():
    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.VERBOSE,
        deferred_tools=ALL_TOOL_FUNCTIONS,
        max_iterations=50,
    )

    result = agent.run(
        user_message=(
            "I have a portfolio of AAPL (25%), MSFT (20%), NVDA (15%), AMZN (15%), "
            "JPM (10%), UNH (10%), and XOM (5%). "
            "\n\n"
            "1. First, run the portfolio allocator on these tickers and weights to get "
            "an optimized allocation suggestion. "
            "\n\n"
            "2. Then deploy a worker agent to do deep research on the macro environment "
            "right now — have it use the macro research tool, earnings call search on "
            "a couple of the top holdings, and pull current US treasury rates and commodity prices. "
            "The worker should write detailed notes on everything it finds. "
            "\n\n"
            "3. After the worker finishes, retrieve its notes, synthesize everything, and "
            "give me a final recommendation: should I rebalance toward the optimized weights, "
            "or does the macro environment suggest a different tilt?"
        ),
        plan_first=True,
        max_iterations=50,
    )

    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(result.answer)
    print("\n" + "=" * 80)
    print(f"Iterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")
    print("=" * 80)


if __name__ == "__main__":
    main()
