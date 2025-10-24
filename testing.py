from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from typing import Protocol
from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.domain.portfolio_operations.optimizer.tool_registry import register_optimizer_tools
from datetime import datetime

class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a test agent",
            user_prompt="What is the capital of France?",
            max_iterations=10,
            plan_first=False,
            save_messages=True,
            model="gpt-4.1",
            verbose=True,
            memory_refresh_interval=20,
            temperature=0.7
        )

    def run(self):
        return super().run()

system_prompt = "You are a financial analyst at a hedge fund."
user_prompt = """
Find me three stocks in the energy sector that are undervalued, have a good growth outlook, and have strong momentum.
Return the tickers to me in json format with the ticker, your reasoning for the pick, and the important metrics that you used to make the pick.
Once you make the picks, construct a macro portfolio centered around the energy tickers you picked.
Create and add proper hedging strategies.
"""

class TestAgentTwo(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_iterations=500,
            plan_first=True,
            save_messages=True,
            model="gpt-5-mini",
            verbose=True,
            memory_refresh_interval=20,
            reasoning_effort="medium",
        )

        register_optimizer_tools(self)

    def run(self):
        return super().run()


agent_two = TestAgentTwo()
agent_two.run()