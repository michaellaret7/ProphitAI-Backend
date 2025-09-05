from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.industry_prompts.beverages import beverages_system_prompt, beverages_user_prompt
from .industry_tools import register_industry_tools

system_prompt = """
Role: Your role is a tester agent that will test the industry tools.
Goal: To test the tools and make sure they are working correctly.

Tools Available:
- calculate_ticker_factors(ticker: str, factor: str) → Calculate all factor metrics for a given ticker and factor type. Can calculate growth, value, momentum, quality, or volatility factors.
- get_industry_benchmark_calculations(industry: str, factor: str) → Get the industry benchmark calculations for a given industry and factor.
- get_sub_industry_benchmark_calculations(sub_industry: str, factor: str) → Get the sub-industry benchmark calculations for a given sub-industry and factor. For the sub-industry arg here use --> soft_drinks_and_non_alcoholic_beverages"
- get_weekly_returns(ticker: str) → Get weekly returns for the last year for a given ticker symbol.
- get_fundamental_data(ticker: str, statement_type: str, quarters_back: int) → Get fundamental financial data for a ticker including income statements, balance sheets, cash flow statements, financial ratios, or analyst estimates.
"""
user_prompt = """
Test the tools and make sure they are working correctly.
"""

class BeveragesAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt, user_prompt, max_iterations=75, plan_first=False, save_messages=True, model="gpt-5", verbose=True, memory_refresh_interval=10)

        register_industry_tools(self)

    def run(self):
        return super().run()

if __name__ == "__main__":
    agent = BeveragesAgent()
    agent.run()
