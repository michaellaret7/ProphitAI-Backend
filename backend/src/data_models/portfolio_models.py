from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

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

class UserCreatedPortfolioAllocations(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    asset_class: str
    allocation: float
    reason: str
    user_id: str
    email: str

class UserCreatedPortfolioThesis(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    generated_at: datetime
    thesis: str
    user_id: str
    email: str

class UserCreatedAvailablePortfolios(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    created_at: datetime
    user_id: str
    email: str

class UserCreatedInvestmentInformation(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    created_at: datetime
    profile: Dict[str, Any]
    user_id: str
    email: str
