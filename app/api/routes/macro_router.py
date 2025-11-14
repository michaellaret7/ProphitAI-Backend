"""Macro data API routes."""

from fastapi import APIRouter, Query
from typing import Optional

from app.api.controller.macro import (
    get_commodity_prices_controller,
    get_bond_rates_controller,
    get_economic_indicator_controller,
    get_economic_calendar_controller,
    get_sector_performance_controller,
    get_sector_pe_controller,
    get_industry_performance_controller,
    get_industry_pe_controller,
)

router = APIRouter(tags=["Macro Data 🌍"])


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


@router.get("/macro/sector/performance")
async def get_sector_performance(
    sector: str = Query(..., description="Sector name (e.g., 'Technology', 'Healthcare', 'Financial Services')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get historical sector performance data.

    ## Overview
    Retrieves historical price performance data for a specific sector, showing percentage changes over time.

    VALID_SECTORS = {
      "Technology",
      "Healthcare",
      "Financial Services",
      "Consumer Cyclical",
      "Consumer Defensive",
      "Industrials",
      "Energy",
      "Utilities",
      "Real Estate",
      "Basic Materials",
      "Communication Services",
  }

    ## Example Usage:
    ```
    GET /api/macro/sector/performance?sector=Technology
    GET /api/macro/sector/performance?sector=Healthcare&startDate=2024-01-01&endDate=2024-12-31
    GET /api/macro/sector/performance?sector=Financial Services&startDate=2024-06-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Sector performance data retrieved successfully",
      "data": {
        "kind": "macro#sectorPerformance",
        "id": "Technology",
        "selfLink": "/api/macro/sector/performance?sector=Technology&startDate=2024-01-01&endDate=2024-12-31",
        "currentItemCount": 252,
        "totalItems": 252,
        "payload": {
          "sector": "Technology",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2024-01-02",
              "changesPercentage": 1.25
            },
            {
              "date": "2024-01-03",
              "changesPercentage": -0.45
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - Sector names are case-insensitive
    - If startDate and endDate are not provided, returns all available data
    - changesPercentage represents daily percentage change
    - Data is cached for 1 day for performance
    - Useful for sector rotation strategies, relative strength analysis, and thematic investing
    """
    return await get_sector_performance_controller(
        sector=sector,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/sector/pe")
async def get_sector_pe(
    sector: str = Query(..., description="Sector name (e.g., 'Technology', 'Healthcare', 'Financial Services')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get historical sector P/E ratio data.

    ## Overview
    Retrieves historical price-to-earnings ratio data for a specific sector, useful for valuation analysis
    and identifying overvalued/undervalued sectors relative to historical norms.

    VALID_SECTORS = {
      "Technology",
      "Healthcare",
      "Financial Services",
      "Consumer Cyclical",
      "Consumer Defensive",
      "Industrials",
      "Energy",
      "Utilities",
      "Real Estate",
      "Basic Materials",
      "Communication Services",
  }

    ## Example Usage:
    ```
    GET /api/macro/sector/pe?sector=Technology
    GET /api/macro/sector/pe?sector=Healthcare&startDate=2023-01-01&endDate=2024-12-31
    GET /api/macro/sector/pe?sector=Energy&startDate=2024-01-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Sector P/E data retrieved successfully",
      "data": {
        "kind": "macro#sectorPE",
        "id": "Technology",
        "selfLink": "/api/macro/sector/pe?sector=Technology&startDate=2023-01-01&endDate=2024-12-31",
        "currentItemCount": 504,
        "totalItems": 504,
        "payload": {
          "sector": "Technology",
          "startDate": "2023-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2023-01-02",
              "pe": 24.56
            },
            {
              "date": "2023-01-03",
              "pe": 24.72
            }
          ]
        }
      }
    }
    ```

    ## Use Cases:
    - **Valuation Analysis**: Compare current P/E to historical averages to identify overvalued/undervalued sectors
    - **Mean Reversion**: Identify sectors trading at extreme P/E multiples likely to revert to mean
    - **Sector Rotation**: Rotate into sectors with attractive valuations relative to history
    - **Earnings Growth**: Combine with performance data to identify sectors with pricing power

    ## Notes:
    - Sector names are case-insensitive
    - If startDate and endDate are not provided, returns all available data
    - P/E ratios are aggregated from constituent companies in each sector
    - Data is cached for 1 day for performance
    - Negative P/E values may indicate sector-wide losses
    """
    return await get_sector_pe_controller(
        sector=sector,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/industry/performance")
async def get_industry_performance(
    industry: str = Query(..., description="Industry name (e.g., 'Software - Application', 'Biotechnology', 'Banks - Regional')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get historical industry performance data.

    ## Overview
    Retrieves historical price performance data for a specific industry, providing more granular analysis
    than sector-level data. Industries are sub-categories within sectors.

    **IMPORTANT**: Industry names must use FMP's specific format (e.g., "Software - Application", not just "Software").

    ## Common Industry Names (FMP Format):

    ### Technology Sector:
    - Software - Application
    - Software - Infrastructure
    - Semiconductors
    - Hardware
    - Electronic Equipment

    ### Healthcare Sector:
    - Biotechnology
    - Drug Manufacturers - General
    - Drug Manufacturers - Specialty & Generic
    - Medical Devices
    - Healthcare Providers & Services

    ### Financial Services Sector:
    - Banks - Regional
    - Banks - Diversified
    - Insurance - Life
    - Insurance - Property & Casualty
    - Asset Management
    - Capital Markets

    ### Consumer Cyclical Sector:
    - Auto Manufacturers
    - Retail - Apparel & Specialty
    - Retail - Cyclical
    - Restaurants
    - Travel & Leisure

    ### Consumer Defensive Sector:
    - Beverages - Non-Alcoholic
    - Beverages - Alcoholic
    - Food Products
    - Household Products
    - Tobacco

    ### Industrials Sector:
    - Aerospace & Defense
    - Construction
    - Machinery
    - Airlines
    - Transportation & Logistics

    ### Energy Sector:
    - Oil & Gas - E&P
    - Oil & Gas - Refining & Marketing
    - Oil & Gas - Equipment & Services
    - Coal

    ### Other:
    - Utilities - Regulated Electric
    - Real Estate - Services
    - Chemicals
    - Metals & Mining
    - Telecom Services

    ## Example Usage:
    ```
    GET /api/macro/industry/performance?industry=Software - Application
    GET /api/macro/industry/performance?industry=Biotechnology&startDate=2024-01-01&endDate=2024-12-31
    GET /api/macro/industry/performance?industry=Banks - Regional&startDate=2024-06-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Industry performance data retrieved successfully",
      "data": {
        "kind": "macro#industryPerformance",
        "id": "Software",
        "selfLink": "/api/macro/industry/performance?industry=Software&startDate=2024-01-01&endDate=2024-12-31",
        "currentItemCount": 252,
        "totalItems": 252,
        "payload": {
          "industry": "Software - Application",
          "startDate": "2024-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2024-01-02",
              "changesPercentage": 1.45
            },
            {
              "date": "2024-01-03",
              "changesPercentage": -0.32
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - Industry names can contain letters, spaces, hyphens, and ampersands
    - If startDate and endDate are not provided, returns all available data
    - changesPercentage represents daily percentage change
    - Data is cached for 1 day for performance
    - More granular than sector data for precise thematic investing
    """
    return await get_industry_performance_controller(
        industry=industry,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/macro/industry/pe")
async def get_industry_pe(
    industry: str = Query(..., description="Industry name (e.g., 'Software - Application', 'Biotechnology', 'Banks - Regional')"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", alias="startDate"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", alias="endDate"),
):
    """
    Get historical industry P/E ratio data.

    ## Overview
    Retrieves historical price-to-earnings ratio data for a specific industry, enabling granular valuation
    analysis at the industry level rather than broad sector level.

    **IMPORTANT**: Industry names must use FMP's specific format (e.g., "Software - Application", not just "Software").

    ## Example Industries by Typical P/E Range:

    ### High-Growth Industries (typically higher P/E):
    - Software - Application (20-40x)
    - Software - Infrastructure (20-40x)
    - Biotechnology (varies, often no earnings)
    - Semiconductors (15-30x)
    - Internet Content & Information (20-35x)

    ### Value Industries (typically lower P/E):
    - Banks - Regional (8-15x)
    - Banks - Diversified (8-15x)
    - Insurance - Life (10-18x)
    - Insurance - Property & Casualty (10-18x)
    - Oil & Gas - E&P (8-12x)
    - Utilities - Regulated Electric (12-20x)

    ### Cyclical Industries:
    - Auto Manufacturers (6-12x)
    - Construction (10-18x)
    - Aerospace & Defense (15-25x)
    - Chemicals (12-20x)
    - Metals & Mining (8-15x)

    ## Example Usage:
    ```
    GET /api/macro/industry/pe?industry=Software - Application
    GET /api/macro/industry/pe?industry=Biotechnology&startDate=2023-01-01&endDate=2024-12-31
    GET /api/macro/industry/pe?industry=Banks - Regional&startDate=2024-01-01
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "Industry P/E data retrieved successfully",
      "data": {
        "kind": "macro#industryPE",
        "id": "Software",
        "selfLink": "/api/macro/industry/pe?industry=Software&startDate=2023-01-01&endDate=2024-12-31",
        "currentItemCount": 504,
        "totalItems": 504,
        "payload": {
          "industry": "Software - Application",
          "startDate": "2023-01-01",
          "endDate": "2024-12-31",
          "data": [
            {
              "date": "2023-01-02",
              "pe": 28.45
            },
            {
              "date": "2023-01-03",
              "pe": 28.62
            }
          ]
        }
      }
    }
    ```

    ## Use Cases:
    - **Relative Valuation**: Compare P/E ratios across related industries (e.g., Software vs. Hardware)
    - **Industry Cycles**: Identify industries at peak/trough valuations
    - **Stock Selection**: Find undervalued stocks within fairly valued industries
    - **Earnings Quality**: Industries with stable P/E ratios may have higher earnings quality

    ## Notes:
    - Industry names can contain letters, spaces, hyphens, and ampersands
    - If startDate and endDate are not provided, returns all available data
    - P/E ratios are aggregated from constituent companies in each industry
    - Data is cached for 1 day for performance
    - Some industries (e.g., Biotechnology) may have negative or very high P/E due to lack of earnings
    - More precise than sector-level P/E for bottom-up analysis
    """
    return await get_industry_pe_controller(
        industry=industry,
        start_date=startDate,
        end_date=endDate,
    )
