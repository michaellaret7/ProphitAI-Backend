from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from app.utils.gpt_parser import canonical_portfolio
from app.models.portfolio_models import PortfolioInput
from app.db.core.db_config import ProphitAltsSession
from app.db.core.prophit_alts_models import FundFinalPosition
from app.utils.decorators.database import with_session
import yaml
from app.utils.serialize_output import serialize_sqlalchemy_obj

@with_session('prophit')
def get_final_portfolio_dict(session=None) -> str:
    """
    Get the initial portfolio dictionary.
    """
    positions_query = session.query(FundFinalPosition).filter(FundFinalPosition.fund_name == "consumer_staples_fund").all()

    final_positions = {}
    for position in positions_query:
        final_positions[position.ticker_name] = {
            "ticker": position.ticker_name,
            "allocation": position.portfolio_allocation,
            "position": position.position.value,
            "thesis": position.reasoning,
        }

    return yaml.dump(final_positions, default_flow_style=False)  

print(get_final_portfolio_dict())