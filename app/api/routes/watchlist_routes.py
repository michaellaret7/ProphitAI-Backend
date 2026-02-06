from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from app.api.controller.watchlist import (
    get_user_watchlists_controller,
    get_watchlist_controller,
    create_watchlist_controller,
    rename_watchlist_controller,
    delete_watchlist_controller,
    add_watchlist_item_controller,
    delete_watchlist_item_controller,
    get_watchlist_metrics_controller,
    get_watchlist_charts_controller,
)
from app.api.auth.clerk import get_clerk_user_id
from app.repositories.user.user import get_all_user_data_by_clerk_id

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


async def get_user_id_from_clerk(clerk_id: str = Depends(get_clerk_user_id)) -> str:
    """Get internal database user_id from Clerk ID."""
    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data.get("id")


class CreateWatchlistRequest(BaseModel):
    name: str


class RenameWatchlistRequest(BaseModel):
    name: str


class AddTickerRequest(BaseModel):
    ticker: str
    priceOnInception: Optional[float] = None


class WatchlistMetricsRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        """Normalize and validate ticker symbols."""
        return [t.upper().strip() for t in v if t.strip()]


class WatchlistChartsRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        """Normalize and validate ticker symbols."""
        return [t.upper().strip() for t in v if t.strip()]


@router.post("/charts")
async def get_watchlist_charts(body: WatchlistChartsRequest):
    """
    Get price charts and correlation data for watchlist tickers.

    Returns 5 years of daily price data and correlation analysis:
    - prices: Daily close prices for each ticker
    - correlations.matrix: Pairwise correlation for each lookback period (1M, 3M, 6M, 9M, 1Y)
    - correlations.rolling: Rolling avg pairwise correlation using window sizes (1M, 3M, 6M, 1Y, 5Y)

    Cache TTL: 3 hours

    Example request body:
    {
        "tickers": ["AAPL", "GOOGL", "TSLA"]
    }
    """
    return await get_watchlist_charts_controller(tickers=body.tickers)


@router.post("/metrics")
async def get_watchlist_metrics(body: WatchlistMetricsRequest):
    """
    Get all financial metrics for watchlist tickers.

    Returns comprehensive financial data for each ticker organized by category:
    - performance: Price change percentages (1D, 5D, 1M, 3M, 6M, YTD, 1Y, 3Y, 5Y)
    - valuation: P/E, PEG, P/B, P/Sales, P/FCF, P/OCF, EV/EBITDA, Div Yield, Payout
    - profitability: Gross/Op/Pretax/Net Margins, Tax Rate, ROA, ROE, ROCE
    - cashFlowLeverage: Per-share metrics, debt ratios, interest coverage
    - operatingMetrics: Liquidity ratios, turnover metrics, cash conversion cycle

    Cache TTL: 24 hours

    Example request body:
    {
        "tickers": ["AAPL", "GOOGL", "TSLA"]
    }
    """
    return await get_watchlist_metrics_controller(tickers=body.tickers)


@router.get("")
async def get_watchlists(user_id: str = Depends(get_user_id_from_clerk)):
    """Get all watchlists for the current user."""
    return await get_user_watchlists_controller(user_id=user_id)


@router.get("/{watchlist_id}")
async def get_watchlist(
    watchlist_id: str = Path(..., description="Watchlist ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get a single watchlist by ID."""
    return await get_watchlist_controller(watchlist_id=watchlist_id, user_id=user_id)


@router.post("")
async def create_watchlist(
    body: CreateWatchlistRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Create a new watchlist."""
    return await create_watchlist_controller(user_id=user_id, name=body.name)


@router.patch("/{watchlist_id}")
async def rename_watchlist(
    body: RenameWatchlistRequest,
    watchlist_id: str = Path(..., description="Watchlist ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Rename an existing watchlist."""
    return await rename_watchlist_controller(
        watchlist_id=watchlist_id, user_id=user_id, name=body.name
    )


@router.delete("/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: str = Path(..., description="Watchlist ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Delete a watchlist."""
    return await delete_watchlist_controller(watchlist_id=watchlist_id, user_id=user_id)


@router.post("/{watchlist_id}/items")
async def add_ticker(
    body: AddTickerRequest,
    watchlist_id: str = Path(..., description="Watchlist ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Add a ticker to a watchlist."""
    return await add_watchlist_item_controller(
        watchlist_id=watchlist_id,
        user_id=user_id,
        ticker=body.ticker,
    )


@router.delete("/{watchlist_id}/items/{ticker}")
async def remove_ticker(
    watchlist_id: str = Path(..., description="Watchlist ID"),
    ticker: str = Path(..., description="Ticker symbol"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Remove a ticker from a watchlist."""
    return await delete_watchlist_item_controller(
        watchlist_id=watchlist_id, user_id=user_id, ticker=ticker
    )
