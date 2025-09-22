import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.agentic_framework.base_agent import BaseAgent
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.builder import BUILD_PORTFOLIO_TOOL

def register(agent):
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_TOOL)
    agent.add_tool(**CORRELATION_MATRIX_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)
    agent.add_tool(**BUILD_PORTFOLIO_TOOL)

if __name__ == "__main__":
    # Enhanced system prompt with explicit portfolio_dict instructions
    system_prompt = """You are a portfolio analysis assistant, tasked with creating portfolios and analyzing their performance."""

    # Modified user prompt to be more explicit
    user_prompt = """Task: 
1. Create a random long-only portfolio with these 8 tickers: ['AAPL', 'MSFT', 'AMZN', 'TSLA', 'META', 'SPY', 'QQQ', 'IWM']
2. Make sure the allocations sum to 1.0 (100%)
3. Calculate the portfolio performance using calculate_portfolio_performance
4. Calculate the portfolio correlation matrix using calculate_portfolio_correlation_matrix
5. Calculate the portfolio factor tilts using calculate_portfolio_factor_tilts
6. Build a portfolio using build_portfolio
7. Once you finish running the portfolio through these tools come up with your own analysis on the portfolio and output it to the assistant.
"""

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        plan_first=False,
        verbose=True,
        model="gpt-5",  # Use a model that actually exists
        max_iterations=100,
        save_messages=False,
        memory_refresh_interval=20,
        use_error_memory=False,
        use_episodic_memory=False,
    )
    
    register(agent)
    result = agent.run()
    print(result)