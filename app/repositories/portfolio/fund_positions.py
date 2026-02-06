"""ProphitAlts fund initial position operations."""

import uuid

from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.db.core.models.market_data_models import *
from app.db.core.models.prophit_alts_models import *
from app.utils.time_utils import get_current_utc_time
from app.utils.decorators.database import with_sessions


@with_sessions(prophit_session='prophit', market_session='market')
def add_initial_positions(positions: dict, industry: str, fund_name: str, prophit_session=None, market_session=None):
    for position in positions['long']:
        prophit_session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=prophit_session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.LONG,
            industry=industry,
            conviction=position['allocation'],  # Already decimal format (0.25 = 25%)
            reasoning=position['reasoning'],
            date_created=get_current_utc_time(),
            date_updated=get_current_utc_time(),
        ))

    for position in positions['short']:
        prophit_session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=prophit_session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.SHORT,
            industry=industry,
            conviction=position['allocation'],  # Already decimal format (0.25 = 25%)
            reasoning=position['reasoning'],
            date_created=get_current_utc_time(),
            date_updated=get_current_utc_time(),
        ))

    # Commit the transaction for prophit_session
    prophit_session.commit()

    return True
