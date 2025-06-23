from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class UserInfo(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime

class UserPortfolioHoldings(BaseModel):
    user_id: str
    fetch_timestamp: datetime
    symbol: str
    sectype: str
    currency: str
    position: float
    marketprice: float
    marketvalue: float
    averagecost: float
    unrealizedpnl: float
    realizedpnl: float
    account: str
    email: str