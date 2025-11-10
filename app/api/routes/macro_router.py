"""Macro data API routes."""

from fastapi import APIRouter, Query
from typing import Optional

from app.api.controller.macro import (
    get_commodity_prices_controller,
    get_bond_rates_controller,
    get_economic_indicator_controller,
    get_economic_calendar_controller,
)

router = APIRouter()


@router.get("/macro/commodities")
async def get_commodity_prices(
    symbol: str = Query(..., description="Commodity symbol (e.g., 'GCUSD' for gold, 'CLUSD' for crude oil)"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get OHLCV price data for a commodity symbol.

    ## Overview
    Retrieves historical open, high, low, close, and volume data for commodity futures and spot prices.

    ## Common Commodity Symbols:
    - **GCUSD**: Gold (USD per troy ounce)
    - **SIUSD**: Silver (USD per troy ounce)
    - **CLUSD**: Crude Oil WTI (USD per barrel)
    - **NGUSD**: Natural Gas (USD per MMBtu)
    - **HGUSD**: Copper (USD per pound)
    - **ZCUSD**: Corn (USD per bushel)
    - **KEUSD**: KC HRW Wheat (USD per bushel)

    ## Example Usage:
    ```
    GET /api/macro/commodities?symbol=GCUSD
    GET /api/macro/commodities?symbol=GCUSD&startDate=2024-01-01&endDate=2024-12-31
    GET /api/macro/commodities?symbol=CLUSD&startDate=2024-06-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Commodity price data retrieved successfully",
      "data": {
        "kind": "macro#commodityPrices",
        "id": "GCUSD",
        "selfLink": "/api/macro/commodities?symbol=GCUSD&startDate=2024-01-01&endDate=2024-12-31",
        "currentItemCount": 252,
        "totalItems": 252,
        "payload": {
          "symbol": "GCUSD",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2024-01-02",
              "open": 2062.50,
              "high": 2088.40,
              "low": 2058.30,
              "close": 2071.80,
              "volume": 123456
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - If startDate and endDate are not provided, returns all available data
    - Data is cached for 1 day for performance
    - Volume may be null for some commodity types
    """
    return await get_commodity_prices_controller(
        symbol=symbol,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/rates")
async def get_bond_rates(
    country: str = Query(..., description="Country code - 2-letter (e.g., 'ES', 'DE') or 3-letter (e.g., 'USA')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get government bond rates (yield curve) for a country.

    ## Overview
    Retrieves historical treasury yields across various maturities from 1 month to 30 years.

    ## Supported Countries:
    - **USA**: United States (note: stored as 3-letter code)
    - **ES**: Spain
    - **DE**: Germany
    - **GB**: United Kingdom
    - **FR**: France
    - **IT**: Italy
    - **JP**: Japan
    - **CA**: Canada
    - **AU**: Australia

    ## Yield Curve Maturities:
    - **Short-term**: 1m, 2m, 3m, 6m
    - **Medium-term**: 1y, 2y, 3y, 5y, 7y
    - **Long-term**: 10y, 20y, 30y

    ## Example Usage:
    ```
    GET /api/macro/rates?country=USA
    GET /api/macro/rates?country=USA&startDate=2024-01-01&endDate=2024-12-31
    GET /api/macro/rates?country=DE&startDate=2024-06-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Government bond rates retrieved successfully",
      "data": {
        "kind": "macro#bondRates",
        "id": "USA",
        "selfLink": "/api/macro/rates?country=USA&startDate=2024-01-01&endDate=2024-12-31",
        "currentItemCount": 252,
        "totalItems": 252,
        "payload": {
          "country": "USA",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2024-01-02",
              "m1": 5.45,
              "m2": 5.48,
              "m3": 5.40,
              "m6": 5.35,
              "y1": 5.02,
              "y2": 4.75,
              "y3": 4.55,
              "y5": 4.35,
              "y7": 4.40,
              "y10": 4.50,
              "y20": 4.75,
              "y30": 4.80
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - If startDate and endDate are not provided, returns all available data
    - Some maturities may be null if not available for specific dates/countries
    - Data is cached for 1 day for performance
    - Useful for yield curve analysis, spread calculations, and rate forecasting
    """
    return await get_bond_rates_controller(
        country=country,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/indicators")
async def get_economic_indicators(
    indicator: str = Query(..., description="Economic indicator name (e.g., 'GDP', 'CPI', 'unemployment_rate')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get economic indicator time series data.

    ## Overview
    Retrieves historical macroeconomic indicator data for fundamental and economic analysis.

    ## Available Indicators:

    ### Labor Market:
    - **unemployment_rate**: Unemployment rate (%)
    - **nonfarm_payrolls**: Non-farm payrolls change (thousands)
    - **jobless_claims**: Initial jobless claims (weekly)
    - **labor_force_participation**: Labor force participation rate (%)

    ### Growth & Output:
    - **GDP**: Gross Domestic Product (billions USD, quarterly)
    - **industrial_production**: Industrial production index
    - **retail_sales**: Retail sales (millions USD, monthly)
    - **capacity_utilization**: Capacity utilization rate (%)

    ### Inflation & Prices:
    - **CPI**: Consumer Price Index
    - **inflation_rate**: Year-over-year inflation rate (%)
    - **PPI**: Producer Price Index
    - **PCE**: Personal Consumption Expenditures Price Index

    ### Credit & Rates:
    - **federal_funds_rate**: Federal Funds Rate (%)
    - **prime_rate**: Bank Prime Loan Rate (%)

    ### Consumer Metrics:
    - **consumer_sentiment**: University of Michigan Consumer Sentiment Index
    - **consumer_confidence**: Conference Board Consumer Confidence Index

    ### Business:
    - **vehicle_sales**: Total vehicle sales (millions, monthly)
    - **housing_starts**: New housing starts (thousands, monthly)

    ## Example Usage:
    ```
    GET /api/macro/indicators?indicator=GDP
    GET /api/macro/indicators?indicator=CPI&startDate=2020-01-01&endDate=2024-12-31
    GET /api/macro/indicators?indicator=unemployment_rate&startDate=2024-01-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Economic indicator data retrieved successfully",
      "data": {
        "kind": "macro#economicIndicator",
        "id": "GDP",
        "selfLink": "/api/macro/indicators?indicator=GDP&startDate=2020-01-01&endDate=2024-12-31",
        "currentItemCount": 20,
        "totalItems": 20,
        "payload": {
          "indicator": "GDP",
          "startDate": "2020-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2020-01-01",
              "value": 21427.7
            },
            {
              "date": "2020-04-01",
              "value": 19520.1
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - If startDate and endDate are not provided, returns all available data
    - Release frequency varies by indicator (weekly, monthly, quarterly, annual)
    - Data is cached for 1 day for performance
    - Values may be null for dates where indicator was not published
    - Useful for economic analysis, recession prediction, and macro strategy
    """
    return await get_economic_indicator_controller(
        indicator=indicator,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/calendar")
async def get_economic_calendar(
    country: str = Query(..., description="Country code (US, UK, CA, FR, DE, IT, JP)"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
    event: Optional[str] = Query(None, description="Event name filter (partial match, case-insensitive)"),
):
    """
    Get economic calendar events for a country.

    ## Overview
    Retrieves scheduled economic data releases and events including actual values, estimates,
    and previous readings for a specific country.

    ## Supported Countries (G7):
    - **US**: United States
    - **UK**: United Kingdom
    - **CA**: Canada
    - **FR**: France
    - **DE**: Germany
    - **IT**: Italy
    - **JP**: Japan

    ## Event Types Include:
    ### Central Bank Events:
    - Interest rate decisions
    - Policy statements
    - Governor speeches
    - Meeting minutes

    ### Labor Market:
    - Unemployment rate
    - Non-farm payrolls
    - Jobless claims
    - Labor force participation

    ### Growth & Output:
    - GDP releases
    - Industrial production
    - Retail sales
    - Manufacturing PMI

    ### Inflation & Prices:
    - CPI (Consumer Price Index)
    - PPI (Producer Price Index)
    - Inflation expectations
    - PCE Price Index

    ### Consumer & Business:
    - Consumer confidence
    - Business sentiment
    - Vehicle sales
    - Housing starts

    ## Example Usage:
    ```
    GET /api/macro/calendar?country=US
    GET /api/macro/calendar?country=US&startDate=2024-01-01&endDate=2024-12-31
    GET /api/macro/calendar?country=US&event=GDP&startDate=2024-01-01
    GET /api/macro/calendar?country=US&event=Fed&startDate=2024-10-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Economic calendar events retrieved successfully",
      "data": {
        "kind": "macro#economicCalendar",
        "id": "US",
        "selfLink": "/api/macro/calendar?country=US&startDate=2024-01-01&endDate=2024-12-31",
        "currentItemCount": 150,
        "totalItems": 150,
        "payload": {
          "country": "US",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "eventFilter": null,
          "data": [
            {
              "eventId": 1234,
              "date": "2024-01-11 13:30:00",
              "event": "Inflation Rate YoY (Dec)",
              "country": "US",
              "currency": "USD",
              "actual": 3.4,
              "previous": 3.1,
              "estimate": 3.2,
              "change": 0.3,
              "changePercentage": 9.677,
              "impact": "High"
            }
          ]
        }
      }
    }
    ```

    ## Impact Levels:
    - **High**: Major market-moving events (GDP, CPI, employment, rate decisions)
    - **Medium**: Significant but less impactful (PMI, sentiment, speeches)
    - **Low**: Minor releases and regional data

    ## Event Filtering:
    Use the `event` parameter to filter by event name:
    - `event=GDP` - All GDP-related events
    - `event=inflation` - All inflation-related events (case-insensitive)
    - `event=Fed` - All Federal Reserve events (speeches, rates, etc.)
    - `event=Michigan` - Michigan consumer sentiment/expectations

    ## Notes:
    - All dates and times are in UTC
    - If startDate and endDate are not provided, returns all available data (3 years historical + 3 years future)
    - `actual` values are populated after event release (null for future events)
    - `estimate` represents consensus forecast
    - `previous` is the prior period's value
    - Data is cached for 1 hour for performance
    - Useful for event-driven trading, economic analysis, and calendar strategies
    """
    return await get_economic_calendar_controller(
        country=country,
        start_date=startDate,
        end_date=endDate,
        event=event,
    )
