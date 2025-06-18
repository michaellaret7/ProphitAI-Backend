from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

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

class UserInfo(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime

class UserCreatedPortfolio(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    asset_class: str
    ticker: str
    allocation: float
    reason: str
    supporting_metrics: Dict[str, Any]
    user_id: str
    email: str

class UserPortfolioAllocations(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    asset_class: str
    allocation: float
    reason: str
    user_id: str
    email: str

class UserPortfolioThesis(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    generated_at: datetime
    thesis: str
    user_id: str
    email: str

class UserPortfolioThesis(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    thesis: str
    user_id: str
    email: str

class UserAvailablePortfolios(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    created_at: datetime
    user_id: str
    email: str

class UserInvestmentInformation(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    created_at: datetime
    profile: Dict[str, Any]
    user_id: str
    email: str

class PriceData(BaseModel):
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


