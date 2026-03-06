from sqlalchemy.orm import session
from app.core.atlas.models.notebook import Notebook
from app.core.atlas.agents.worker_agent import WorkerAgent
from app.core.atlas.tools.options.expirations import get_option_expirations
from app.core.atlas.tools.options.contracts import get_option_contracts
from app.core.atlas.tools.options.chain import get_options_chain
from app.core.atlas.tools.options.quote import get_option_quote
from app.core.atlas.tools.options.price_history import get_option_price_history
from app.core.atlas.tools.broker.options_trade import propose_options_trade, propose_multi_leg_options_trade
from app.core.atlas.tools.broker.trade import propose_trade
from app.core.atlas.tools.broker.portfolio import get_positions, close_position
from app.core.atlas.tools.broker.account import account_info
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User
from app.utils.serialize_output import serialize_sqlalchemy_obj


us = UserSession()
all_users = us.query(User).filter(User.email == "sam_altman+clerk_test@gmail.com").first()
print(serialize_sqlalchemy_obj(all_users))
us.close()

# task = """
# Instructions:
# - Review the users portfolio (michaellaret7@gmail.com) 
# - run a risk analysis on the portfolio
# - propose a multi-leg options trade on the portfolio to mitigate risk
# """

# worker = WorkerAgent(
#     task=task,
#     tools=[
#         get_option_expirations.tool,
#         get_option_contracts.tool,
#         get_options_chain.tool,
#         get_option_quote.tool,
#         get_option_price_history.tool,
#         propose_options_trade.tool,
#         propose_multi_leg_options_trade.tool,
#         propose_trade.tool,
#         get_positions.tool,
#         close_position.tool,
#         account_info.tool,
#     ],
#     notebook=Notebook(),
# )

# result = worker.run()
# print(result.answer)
