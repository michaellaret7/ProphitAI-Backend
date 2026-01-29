from app.core.atlas.agents.chat_agent import ChatAgent
from app.core.atlas.tools.portfolio.get_user_portfolio import get_user_portfolio, GET_USER_PORTFOLIO_TOOL
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio, User
from app.core.atlas.tools.data.screening import EQUITY_SCREENER_TOOL
from app.core.atlas.tools.ticker.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL

user_session = UserSession()
portfolio = user_session.query(Portfolio).join(User).filter(User.email == "michaellaret7@gmail.com").all()

portfolio_id = [p.id for p in portfolio]
portfolio_id = portfolio_id[1]
user_session.close()

print(portfolio_id)

print(get_user_portfolio(portfolio_id))

agent = ChatAgent(
    system_prompt="You are a helpful assistant that can answer questions and help with tasks.",
)

agent.add_tool(**GET_USER_PORTFOLIO_TOOL)
agent.add_tool(**EQUITY_SCREENER_TOOL)
agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)

agent.run_interactive(session_id="test")