from app.db.core.db_config import ProphitAltsSession
from app.db.core.models.prophit_alts_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.decorators.database import with_session
from typing import Optional, List
import uuid

@with_session('prophit')
def get_fund_final_positions(fund_name: str, session=None) -> List[dict]:
    """
    Query fund final positions from the database.
    
    Args:
        fund_name (str): Name of the fund to filter by
        
    Returns:
        List[dict]: List of serialized final position records
    """
    # Join with Fund table to filter by name
    query = session.query(FundFinalPosition).join(Fund).filter(Fund.fund_name == fund_name)
    
    # Order by date_updated descending to get most recent first
    query = query.order_by(FundFinalPosition.date_updated.desc())
    
    # Execute query
    positions = query.all()
    
    # Serialize results
    serialized_positions = [serialize_sqlalchemy_obj(position) for position in positions]
    
    return serialized_positions

@with_session('prophit')
def get_fund_table(session=None) -> List[dict]:
    """
    Query fund table from the database.
    """
    query = session.query(Fund)
    table = query.all()

    return [serialize_sqlalchemy_obj(t) for t in table]

if __name__ == "__main__":
    table = get_fund_table()
    print(table)