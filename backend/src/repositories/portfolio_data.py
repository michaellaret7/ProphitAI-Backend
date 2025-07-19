from backend.src.db.core.db_config import UserSession, MarketSession, ProphitAltsSession
from backend.src.db.core.user_data_models import *
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from typing import Optional
import uuid
from datetime import datetime, timedelta
from backend.src.db.core.market_data_models import *
from sqlalchemy import func
from sqlalchemy.orm import aliased
from backend.src.db.core.prophit_alts_models import *

def retrieve_portfolio(email: str = None, workos_id: str = None, user_id: uuid.UUID = None, is_current: bool = None, portfolio_id: uuid.UUID = None):
    session = UserSession()
    
    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    elif workos_id:
        user = session.query(User).filter(User.workos_id == workos_id).first()
    else:
        session.close()
        raise ValueError("At least one identifier (email, workos_id, or user_id) must be provided")
    
    if not user:
        session.close()
        return []
    
    # Build the query based on parameters
    query = session.query(Portfolio).filter(Portfolio.user_id == user.id)
    
    if is_current:
        query = query.filter(Portfolio.is_current == True)
    elif portfolio_id:
        query = query.filter(Portfolio.portfolio_id == portfolio_id)
    
    portfolio = query.all()
    portfolio = [serialize_sqlalchemy_obj(p) for p in portfolio]
    
    session.close()
    return portfolio

def add_portfolio(portfolio, company_name, user_email, portfolio_name):
    user_session = UserSession()
    market_session = MarketSession()

    company_id = user_session.query(Company).filter(Company.name == company_name).first().id
    user_id = user_session.query(User).filter(User.email == user_email).first().id
    portfolio_uuid = uuid.uuid4()

    for positions in portfolio:
        user_session.add(Portfolio(
            portfolio_id=portfolio_uuid,
            name=portfolio_name,
            ticker=positions.ticker,
            sector=market_session.query(Ticker).filter(Ticker.ticker == positions.ticker).first().sector,
            industry=market_session.query(Ticker).filter(Ticker.ticker == positions.ticker).first().industry,
            sub_industry=market_session.query(Ticker).filter(Ticker.ticker == positions.ticker).first().sub_industry,
            allocation=positions.allocation,
            is_current=False,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            company_id=company_id,
            user_id=user_id,
        ))

    user_session.commit()
    user_session.close()
    market_session.close()

def list_portfolios(email: str = None, workos_id: str = None, user_id: uuid.UUID = None):
    session = UserSession()
    
    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    elif workos_id:
        user = session.query(User).filter(User.workos_id == workos_id).first()
    else:
        session.close()
        raise ValueError("At least one identifier (email, workos_id, or user_id) must be provided")
    
    if not user:
        session.close()
        return []
    
    # Create a subquery with row numbers partitioned by portfolio_id
    subquery = session.query(
        Portfolio.portfolio_id,
        Portfolio.name,
        Portfolio.is_current,
        Portfolio.created_date,
        Portfolio.company_id,
        Portfolio.user_id,
        func.row_number().over(
            partition_by=Portfolio.portfolio_id,
            order_by=Portfolio.created_date
        ).label('row_num')
    ).filter(Portfolio.user_id == user.id).subquery()
    
    # Query only the first row from each portfolio with specific columns
    portfolios = session.query(
        subquery.c.portfolio_id,
        subquery.c.name,
        subquery.c.is_current,
        subquery.c.created_date,
        subquery.c.company_id,
        subquery.c.user_id
    ).filter(
        subquery.c.row_num == 1
    ).all()
    
    # Convert to list of dictionaries
    result = []
    for row in portfolios:
        result.append({
            'portfolio_id': str(row.portfolio_id),
            'name': row.name,
            'is_current': row.is_current,
            'created_date': row.created_date.isoformat() if row.created_date else None,
            'company_id': str(row.company_id) if row.company_id else None,
            'user_id': str(row.user_id)
        })
    
    session.close()
    return result

def add_initial_positions(positions: dict, industry: str, fund_name: str):
    session = ProphitAltsSession()
    market_session = MarketSession()

    for position in positions['long']:
        session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.LONG,
            industry=industry,
            risk_allocation=position['allocation']/100,
            reasoning=position['reasoning'],
            date_created=datetime.now(),
            date_updated=datetime.now(),
        ))

    for position in positions['short']:
        session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.SHORT,
            industry=industry,
            risk_allocation=position['allocation']/100,
            reasoning=position['reasoning'],
            date_created=datetime.now(),
            date_updated=datetime.now(),
        ))   

    session.commit()
    session.close()
    market_session.close()

    return True