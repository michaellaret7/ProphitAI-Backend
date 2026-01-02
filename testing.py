from app.core.agentic_framework.base_agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.messages.agent_message import UNIVERSAL_AGENT_MESSAGE
from datetime import datetime
from app.core.agentic_framework.base_agent.utils.models import PrintMode

# agent = BaseAgent(
#     system_prompt=UNIVERSAL_AGENT_MESSAGE,
#     user_prompt="Use the web search tool to search for the latest news on the US economy and financial markets.",
#     provider="groq",
#     model="Kimi-K2-instruct",
#     max_iterations=10,
#     print_mode=PrintMode.VERBOSE,
#     plan_first=True
# )

# result = agent.run()
# print(result)

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio

with UserSession() as session:
    portfolios = session.query(Portfolio).all()
    for item in portfolios:
        print(item.nav)
        # item.nav = 10_000_000

