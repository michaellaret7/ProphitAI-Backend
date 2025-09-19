from app.db.core.market_data_models import *
from app.db.core.db_config import MarketSession, ProphitAltsSession
from app.db.core.prophit_alts_models import *
from app.utils.gpt_parser import parse_portfolio_with_gpt
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.industry_agents.agents import IndustryAgent
import json

session = ProphitAltsSession()
initial_positions = session.query(FundInitialPosition).filter(FundInitialPosition.fund_name == "consumer_staples_fund").all()
print(initial_positions)
for position in initial_positions:
    print(position.ticker_name)
    print(position.position)
    print(position.conviction)
    print(position.reasoning)
    print("-"*100)


