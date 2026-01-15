from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.callbacks.state_callback import StateCallback
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from typing import Optional
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio, User
from app.domain.portfolio_insights.tool_registry import register_portfolio_insights_tools
from .models import InsightsResponseModel
from .prompts import build_prompts


class PortfolioInsightsAgent(BaseAgent):
    response_model = InsightsResponseModel

    def __init__(
        self,
        portfolio_id: str,
        print_mode: str = PrintMode.VERBOSE,
        state_callback: Optional[StateCallback] = None,
    ):
        self.portfolio_id = portfolio_id
        self.system_prompt, self.user_prompt = build_prompts(portfolio_id)

        super().__init__(
            provider="openai",
            model="gpt-5.2",
            system_prompt=self.system_prompt,
            user_prompt=self.user_prompt,
            max_iterations=200,
            plan_first=True,
            print_mode=print_mode,
            state_callback=state_callback,
        )

        register_portfolio_insights_tools(self)
    
if __name__ == "__main__":
    user_session = UserSession()
    portfolio = user_session.query(Portfolio).join(User).filter(User.email == "michaellaret7@gmail.com").all()

    portfolio_id = [p.id for p in portfolio]
    portfolio_id = portfolio_id[1]
    user_session.close()

    agent = PortfolioInsightsAgent(portfolio_id=str(portfolio_id))
    prompt = agent.user_prompt
    x = agent.run(response_format=InsightsResponseModel)
    print(x)
