"""Technical analysis API routes."""

from fastapi import APIRouter, Query
from typing import Optional

from prophitai_api.controllers.technical import get_technical_indicators_controller

router = APIRouter(tags=["Technical Analysis 📉"])


@router.get("/technical/indicators")
async def get_technical_indicators(
    ticker: str = Query(..., description="Stock ticker symbol"),
    startDate: str = Query(..., description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: str = Query(..., description="End date (YYYY-MM-DD)", alias="endDate"),
    indicators: Optional[str] = Query(
        None,
        description="Comma-separated list of indicators (e.g., 'rsi,macd,bollinger_bands'). If not provided, returns all indicators.",
    ),
):
    """
    Calculate technical indicators for a stock ticker over a date range.

    ## Available Indicators:
    - **rsi**: Relative Strength Index (14-period)
    - **macd**: MACD (12, 26, 9)
    - **adx**: Average Directional Index
    - **roc**: Rate of Change (12-month momentum)
    - **bollinger_bands**: Bollinger Bands (20-period, 2 std)
    - **atr**: Average True Range
    - **donchian_channels**: Donchian Channels
    - **keltner_channels**: Keltner Channels
    - **vwap**: Volume Weighted Average Price
    - **obv**: On-Balance Volume
    - **cmf**: Chaikin Money Flow
    - **mfi**: Money Flow Index
    - **moving_averages**: Moving Averages (SMA 20, 50, 100, 200)

    ## Example Usage:
    ```
    GET /api/technical/indicators?ticker=AAPL&startDate=2024-01-01&endDate=2024-12-31
    GET /api/technical/indicators?ticker=AAPL&startDate=2024-01-01&endDate=2024-12-31&indicators=rsi,macd
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "data": {
        "kind": "technical#indicators",
        "id": "AAPL",
        "payload": {
          "ticker": "AAPL",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "indicators": {
            "rsi": [
              {"date": "2024-01-01", "value": 65.3},
              {"date": "2024-01-02", "value": 66.1}
            ],
            "macd": [
              {"date": "2024-01-01", "macd": 2.5, "signal": 1.8, "hist": 0.7}
            ]
          }
        }
      },
      "message": "Technical indicators retrieved successfully"
    }
    ```
    """
    # Parse indicators list if provided
    indicator_list = None
    if indicators:
        indicator_list = [ind.strip() for ind in indicators.split(",")]

    return await get_technical_indicators_controller(
        ticker=ticker,
        start_date=startDate,
        end_date=endDate,
        indicators=indicator_list,
    )
