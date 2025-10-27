"""Test ticker comparison using SimpleAgent with ticker tools.

This test demonstrates:
1. Registering multiple ticker analysis tools
2. Agent reasoning and comparing two stocks
3. Agent thinking out loud through the analysis
"""

from app.core.agentic_framework.base_agent_v2 import SimpleAgent
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    get_ticker_performance_and_risk,
    GET_TICKER_PERFORMANCE_AND_RISK_DESCRIPTION,
    GET_TICKER_PERFORMANCE_AND_RISK_PARAMETERS
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import (
    calculate_ticker_factors,
    CALCULATE_TICKER_FACTORS_DESCRIPTION,
    CALCULATE_TICKER_FACTORS_PARAMETERS
)
from app.core.agentic_framework.tool_lib.ticker_tools.weekly_returns import (
    get_weekly_returns,
    GET_WEEKLY_RETURNS_DESCRIPTION,
    GET_WEEKLY_RETURNS_PARAMETERS
)
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode

def test_ticker_comparison():
    """Test comparing two tickers using the SimpleAgent."""

    # System prompt with explicit instructions to reason out loud
    system_prompt = """You are an expert financial analyst helping investors make informed decisions.

Your task is to compare two stocks and determine which one is a better buy right now.

IMPORTANT INSTRUCTIONS:
1. Think out loud - explain your reasoning step by step
2. Use the available tools to gather comprehensive data on both stocks
3. Analyze key metrics like:
   - Performance metrics (Sharpe, Sortino, returns)
   - Risk metrics (volatility, max drawdown, beta)
   - Factor exposures (growth, value, quality, momentum)
   - Recent performance trends (weekly returns)
4. Consider multiple perspectives before making your recommendation
5. Be thorough - don't rush to a conclusion
6. When you have enough information and have reasoned through it, provide a clear recommendation

When you're ready with your final recommendation, output:
'Final Answer:' followed by your detailed analysis and recommendation."""

    user_prompt = """
    Goal: Compare AAPL (Apple) and MSFT (Microsoft) and tell me which one is a better buy right now. Be thorough in your analysis and explain your reasoning.
    
    Your thinking framework should be:
    - Think about the task
    - Call a tool for both of the tickers to get the data you need
    - Observe and analyze the data
    - Reason about the data
    - Move on the the next tool call round until you have all the data you need

    Notes:
    - The only data you need will be available in the tools you have access to.

    Example of a good response:
    - Final Answer: AAPL is a better buy right now because of X, Y, and Z.
    """

    # Initialize agent
    agent = SimpleAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",
        max_iterations=30,
        print_mode=PrintMode.VERBOSE,
        reasoning_effort="high",
        temperature=0.7
    )

    # Register ticker tools
    agent.add_tool(
        name="get_ticker_performance_and_risk",
        description=GET_TICKER_PERFORMANCE_AND_RISK_DESCRIPTION,
        parameters=GET_TICKER_PERFORMANCE_AND_RISK_PARAMETERS,
        function=get_ticker_performance_and_risk
    )

    agent.add_tool(
        name="calculate_ticker_factors",
        description=CALCULATE_TICKER_FACTORS_DESCRIPTION,
        parameters=CALCULATE_TICKER_FACTORS_PARAMETERS,
        function=calculate_ticker_factors
    )

    agent.add_tool(
        name="get_weekly_returns",
        description=GET_WEEKLY_RETURNS_DESCRIPTION,
        parameters=GET_WEEKLY_RETURNS_PARAMETERS,
        function=get_weekly_returns
    )

    print("\n" + "="*80)
    print("STOCK COMPARISON ANALYSIS: AAPL vs MSFT")
    print("="*80)

    # Run agent
    result = agent.run()

    # Print final results
    print("\n" + "="*80)
    print("FINAL RECOMMENDATION")
    print("="*80)
    print(result['final_answer'])
    print("\n" + "="*80)
    print(f"Analysis completed in {result['iterations']} iterations")
    print(f"Total tokens used: {result['total_tokens']}")
    print(f"Stop reason: {result['stop_reason']}")
    print("="*80)

    return result

if __name__ == "__main__":
    # Run the main ticker comparison test
    print("\n" + "#"*80)
    print("# TEST 1: COMPREHENSIVE STOCK COMPARISON (AAPL vs MSFT)")
    print("#"*80)
    test_ticker_comparison()


