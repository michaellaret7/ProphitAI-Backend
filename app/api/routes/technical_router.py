"""Technical analysis API routes."""

from enum import Enum
from fastapi import APIRouter, Query
from typing import Optional, List

from app.api.controller.technical import (
    get_technical_indicators_controller,
    get_pivot_points_controller,
)

router = APIRouter(tags=["Technical Analysis 📉"])


class PivotType(str, Enum):
    """Supported pivot point calculation types."""
    CLASSIC = "classic"
    FIBONACCI = "fibonacci"
    CAMARILLA = "camarilla"
    WOODIE = "woodie"
    DEMARK = "demark"


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
    - **bollinger_bands**: Bollinger Bands (20-period, 2 std)
    - **stoch**: Stochastic Oscillator
    - **stoch_rsi**: Stochastic RSI
    - **adx**: Average Directional Index
    - **williams_r**: Williams %R
    - **cci**: Commodity Channel Index
    - **atr**: Average True Range
    - **ultimate_oscillator**: Ultimate Oscillator
    - **roc**: Rate of Change
    - **bull_bear_power**: Elder's Bull and Bear Power
    - **vwap**: Volume Weighted Average Price
    - **donchian_channels**: Donchian Channels
    - **keltner_channels**: Keltner Channels
    - **parabolic_sar**: Parabolic SAR
    - **moving_averages**: Moving Averages (20, 50, 100, 200)

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


@router.get("/technical/pivot-points")
async def get_pivot_points(
    ticker: str = Query(..., description="Stock ticker symbol"),
    startDate: str = Query(..., description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: str = Query(..., description="End date (YYYY-MM-DD)", alias="endDate"),
    pivotType: PivotType = Query(
        PivotType.CLASSIC,
        description="Type of pivot points",
        alias="pivotType",
    ),
):
    """
    Calculate pivot points for a stock ticker over a date range.

    ## Pivot Point Types:
    - **classic**: Classic pivot points (default)
      - Uses (H + L + C) / 3
      - Standard support/resistance levels
    - **fibonacci**: Fibonacci pivot points
      - Uses Fibonacci ratios (0.382, 0.618, 1.000)
    - **camarilla**: Camarilla pivot points
      - Uses close + multipliers of range
      - Tighter levels for intraday trading
    - **woodie**: Woodie's pivot points
      - Uses (H + L + 2C) / 4
      - Weights close price more heavily
    - **demark**: DeMark's pivot points
      - Conditional calculation based on O/H/L/C relationship
      - Only provides R1, S1, and pivot

    ## Example Usage:
    ```
    GET /api/technical/pivot-points?ticker=AAPL&startDate=2024-01-01&endDate=2024-12-31
    GET /api/technical/pivot-points?ticker=AAPL&startDate=2024-01-01&endDate=2024-12-31&pivotType=fibonacci
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "data": {
        "kind": "technical#pivotPoints",
        "id": "AAPL",
        "payload": {
          "ticker": "AAPL",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "pivotType": "classic",
          "pivotPoints": [
            {
              "date": "2024-01-01",
              "s3": 150.2,
              "s2": 152.5,
              "s1": 154.8,
              "pivot": 157.1,
              "r1": 159.4,
              "r2": 161.7,
              "r3": 164.0
            }
          ]
        }
      },
      "message": "Classic pivot points retrieved successfully"
    }
    ```

    ## Notes:
    - Pivot points use previous period's OHLC data
    - First row will have NaN values (no previous period)
    - DeMark pivots only provide R1, S1, and pivot (R2, R3, S2, S3 will be null)
    """
    return await get_pivot_points_controller(
        ticker=ticker,
        start_date=startDate,
        end_date=endDate,
        pivot_type=pivotType.value,
    )
