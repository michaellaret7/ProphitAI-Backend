from app.db.core.db_config import ProphitAltsSession
from app.db.core.prophit_alts_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from typing import Optional, List
import uuid

def get_fund_final_positions(fund_name: str) -> List[dict]:
    """
    Query fund final positions from the database.
    
    Args:
        fund_name (str): Name of the fund to filter by
        
    Returns:
        List[dict]: List of serialized final position records
    """
    session = ProphitAltsSession()
    
    try:
        # Join with Fund table to filter by name
        query = session.query(FundFinalPosition).join(Fund).filter(Fund.fund_name == fund_name)
        
        # Order by date_updated descending to get most recent first
        query = query.order_by(FundFinalPosition.date_updated.desc())
        
        # Execute query
        positions = query.all()
        
        # Serialize results
        serialized_positions = [serialize_sqlalchemy_obj(position) for position in positions]
        
        return serialized_positions
        
    finally:
        session.close()
