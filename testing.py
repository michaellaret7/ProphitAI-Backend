from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from typing import Protocol
from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.domain.portfolio_operations.optimizer.tool_registry import register_optimizer_tools

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
            memory_refresh_interval=20
        )

    def run(self):
        return super().run()

class TestAgentTwo(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a financial analyst at a hedge fund.",
            user_prompt="Find me three stocks in the energy sector that are undervalued and have a good growth outlook.",
            max_iterations=100,
            plan_first=True,
            save_messages=True,
            model="gpt-5-mini",
            verbose=True,
            memory_refresh_interval=20
        )

        register_optimizer_tools(self)

    def run(self):
        return super().run()

agent = TestAgent()
agent.run()

agent_two = TestAgentTwo()
agent_two.run()