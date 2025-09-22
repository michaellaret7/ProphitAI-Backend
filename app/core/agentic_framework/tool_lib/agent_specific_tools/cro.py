from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from app.utils.gpt_parser import canonical_portfolio
from app.models.portfolio_models import PortfolioInput
from app.db.core.db_config import ProphitAltsSession
from app.db.core.prophit_alts_models import FundInitialPosition, Fund
from app.utils.decorators.database import with_session

# Consumer Staples Fund initial portfolio configuration
INITIAL_PORTFOLIO_DICT = {
    # Long positions
    "CASY": {"conviction": 0.10, "position": "long"},
    "CELH": {"conviction": 0.10, "position": "long"},
    "ODC": {"conviction": 0.05, "position": "long"},
    "ODD": {"conviction": 0.05, "position": "long"},
    "PM": {"conviction": 0.05, "position": "long"},
    "VITL": {"conviction": 0.05, "position": "long"},
    "WMT": {"conviction": 0.05, "position": "long"},
    "BJ": {"conviction": 0.05, "position": "long"},
    "SFM": {"conviction": 0.05, "position": "long"},
    "COCO": {"conviction": 0.05, "position": "long"},
    "MNST": {"conviction": 0.05, "position": "long"},
    "CL": {"conviction": 0.05, "position": "long"},
    "IPAR": {"conviction": 0.05, "position": "long"},
    "TPB": {"conviction": 0.05, "position": "long"},
    "DOLE": {"conviction": 0.05, "position": "long"},
    "PPC": {"conviction": 0.05, "position": "long"},
    "INGR": {"conviction": 0.05, "position": "long"},
    # Short positions
    "WBA": {"conviction": 0.05, "position": "short"},
    "ANDE": {"conviction": 0.05, "position": "short"},
    "TGT": {"conviction": 0.02, "position": "short"},
    "STZ": {"conviction": 0.05, "position": "short"},
    "PEP": {"conviction": 0.05, "position": "short"},
    "SAM": {"conviction": 0.05, "position": "short"},
    "MGPI": {"conviction": 0.05, "position": "short"},
    "ENR": {"conviction": 0.05, "position": "short"},
    "SPB": {"conviction": 0.05, "position": "short"},
    "COTY": {"conviction": 0.05, "position": "short"},
    "KVUE": {"conviction": 0.05, "position": "short"},
    "KLG": {"conviction": 0.05, "position": "short"},
    "JJSF": {"conviction": 0.05, "position": "short"},
    "SEB": {"conviction": 0.05, "position": "short"}
}


@with_session('prophit')
def get_initial_portfolio_dict(session=None):
    """
    Get the initial portfolio dictionary.
    """
    initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

    INITIAL_PORTFOLIO_DICT = {}

    for position in initial_positions:
        INITIAL_PORTFOLIO_DICT[position.ticker_name] = {
            "conviction": position.conviction,
            "position": position.position.value
        }
    
    INITIAL_PORTFOLIO_DICT = {t: {"allocation": float(p.conviction), "position": p.position.value} for t, p in INITIAL_PORTFOLIO_DICT.items()}

    return INITIAL_PORTFOLIO_DICT   
