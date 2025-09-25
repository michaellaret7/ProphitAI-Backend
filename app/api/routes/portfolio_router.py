from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.api.controller.portfolio_controller import (
    get_user_portfolio_list_controller,
    create_portfolio_controller,
    update_portfolio_controller,
    delete_portfolio_controller,
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

@router.get("/user/portfolios")
async def get_user_portfolio_list(email: str = Query(None, description="User's email address")):
    """
    Get user portfolio list by email
    
    Email must be provided.
    """
    return await get_user_portfolio_list_controller(email=email)

@router.post("/user/portfolios", status_code=201)
async def create_portfolio(body: CreatePortfolioRequest):
    return await create_portfolio_controller(
        email=body.email,
        company_name=body.companyName,
        portfolio_name=body.portfolioName,
        positions=[p.dict() for p in body.positions],
    )

@router.patch("/user/portfolios")
async def patch_portfolio(body: UpdatePortfolioRequest):
    return await update_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
        name=body.name,
        is_current=body.isCurrent,
    )


class DeletePortfolioRequest(BaseModel):
    email: EmailStr
    portfolioId: str


@router.delete("/user/portfolios")
async def delete_portfolio(body: DeletePortfolioRequest):
    return await delete_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
    )

