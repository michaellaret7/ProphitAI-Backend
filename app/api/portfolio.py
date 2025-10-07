from fastapi import APIRouter
from app.api.routes.portfolio_router import router as portfolio_routes

router = APIRouter()

router.include_router(portfolio_routes, tags=["portfolios"])