from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.api.controller.portfolio_controller import (
    get_user_portfolio_list_controller,
    create_portfolio_controller,
    update_portfolio_controller,
    delete_portfolio_controller,
    get_portfolio_returns_controller,
)

router = APIRouter()

class PositionModel(BaseModel):
    ticker: str
    allocation: float

class CreatePortfolioRequest(BaseModel):
    email: EmailStr
    companyName: str
    portfolioName: str
    positions: List[PositionModel]

class UpdatePortfolioRequest(BaseModel):
    email: EmailStr
    portfolioId: str
    name: Optional[str] = None
    isCurrent: Optional[bool] = None

class DeletePortfolioRequest(BaseModel):
    email: EmailStr
    portfolioId: str

class PortfolioReturnsRequest(BaseModel):
    email: EmailStr = "michaellaret7@gmail.com"
    portfolioId: str = "01be5cf2-a1fe-45b0-b9a4-cf9cc1a94b36"

#TODO: We want to get the portfolios by uuid
@router.get("/portfolios")
async def get_user_portfolio_list(email: str = Query(None, description="User's email address")):
    """
    Get user portfolio list by email
    
    Email must be provided.
    """
    return await get_user_portfolio_list_controller(email=email)

@router.post("/portfolios", status_code=201)
async def create_portfolio(body: CreatePortfolioRequest):
    return await create_portfolio_controller(
        email=body.email,
        company_name=body.companyName,
        portfolio_name=body.portfolioName,
        positions=[p.dict() for p in body.positions],
    )

@router.patch("/portfolios")
async def patch_portfolio(body: UpdatePortfolioRequest):
    return await update_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
        name=body.name,
        is_current=body.isCurrent,
    )

@router.delete("/portfolios")
async def delete_portfolio(body: DeletePortfolioRequest):
    return await delete_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
    )

@router.post("/portfolios/returns")
async def get_portfolio_returns(body: PortfolioReturnsRequest):
    return await get_portfolio_returns_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
    )

