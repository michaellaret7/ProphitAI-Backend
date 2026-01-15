"""ETF data API routes."""

from fastapi import APIRouter, Path

from app.api.controller.etf import (
    get_etf_info_controller,
    get_etf_holdings_controller,
    get_etf_country_weightings_controller,
    get_batch_etf_info_controller,
)
from app.models.etf_models import BatchETFInfoRequest

router = APIRouter(tags=["ETF Data 📊"])


@router.get("/etf/{symbol}/info")
async def get_etf_info(
    symbol: str = Path(..., description="ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')"),
):
    """
    Get comprehensive ETF information and metadata.

    ## Overview
    Retrieves detailed information about an ETF including basic info, asset classification,
    financial metrics, sector exposure, and trading data.

    ## Response Includes:
    ### Basic Information:
    - Symbol and name
    - Description and investment strategy
    - Inception date
    - ETF company/issuer
    - Domicile and ISIN

    ### Financial Metrics:
    - Assets under management (AUM)
    - Expense ratio
    - Average volume
    - NAV (Net Asset Value)
    - Holdings count

    ### Exposure:
    - Asset class
    - Sector breakdown (sectorsList)
    - Category and focus

    ## Example Usage:
    ```
    GET /api/etf/SPY/info
    GET /api/etf/QQQ/info
    GET /api/etf/VTI/info
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "ETF information retrieved successfully",
      "data": {
        "kind": "etf#info",
        "id": "SPY",
        "selfLink": "/api/etf/SPY/info",
        "currentItemCount": 1,
        "totalItems": 1,
        "payload": {
          "symbol": "SPY",
          "info": {
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "description": "Seeks to track the S&P 500 Index...",
            "assetClass": "Large Cap Equity",
            "etfCompany": "State Street",
            "inceptionDate": "1993-01-22",
            "assetsUnderManagement": 500000000000,
            "expenseRatio": 0.0945,
            "avgVolume": 50000000,
            "holdingsCount": 503,
            "nav": 550.25,
            "sectorsList": [
              {
                "industry": "Technology",
                "exposure": 28.5
              }
            ]
          }
        }
      }
    }
    ```

    ## Notes:
    - Data is cached for 1 day for performance
    - Includes comprehensive sector exposure via sectorsList
    - All financial metrics are current as of the last update
    """
    return await get_etf_info_controller(symbol=symbol)


@router.get("/etf/{symbol}/holdings")
async def get_etf_holdings(
    symbol: str = Path(..., description="ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')"),
):
    """
    Get complete ETF holdings data.

    ## Overview
    Retrieves detailed holdings information for an ETF, including all constituent securities
    with their weights, market values, and share counts.

    ## Holdings Include:
    - Ticker symbol of holding
    - Asset name
    - Security name
    - ISIN and CUSIP identifiers
    - Shares held
    - Weight percentage in portfolio
    - Market value of position

    ## Example Usage:
    ```
    GET /api/etf/SPY/holdings
    GET /api/etf/QQQ/holdings
    GET /api/etf/VTI/holdings
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "ETF holdings retrieved successfully",
      "data": {
        "kind": "etf#holdings",
        "id": "SPY",
        "selfLink": "/api/etf/SPY/holdings",
        "currentItemCount": 503,
        "totalItems": 503,
        "payload": {
          "symbol": "SPY",
          "holdings": [
            {
              "symbol": "SPY",
              "asset": "AAPL",
              "name": "APPLE INC",
              "isin": "US0378331005",
              "securityCusip": "037833100",
              "sharesNumber": 178000000,
              "weightPercentage": 7.2,
              "marketValue": 45000000000
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - Data is cached for 1 day for performance
    - Holdings are returned as provided by the data source
    - Total market value and weight percentage sum to approximately 100%
    - Useful for portfolio overlap analysis, concentration risk assessment
    """
    return await get_etf_holdings_controller(symbol=symbol)


@router.get("/etf/{symbol}/countries")
async def get_etf_country_weightings(
    symbol: str = Path(..., description="ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')"),
):
    """
    Get ETF country exposure weightings.

    ## Overview
    Retrieves geographic concentration data showing how the ETF's holdings are distributed
    across different countries.

    ## Country Weightings Include:
    - Country name
    - Exposure percentage
    - Market value by country

    ## Example Usage:
    ```
    GET /api/etf/SPY/countries
    GET /api/etf/VEA/countries  # Vanguard FTSE Developed Markets ETF
    GET /api/etf/EEM/countries  # iShares MSCI Emerging Markets ETF
    ```

    ## Response Format:
    ```json
    {
      "status": 200,
      "message": "ETF country weightings retrieved successfully",
      "data": {
        "kind": "etf#countryWeightings",
        "id": "SPY",
        "selfLink": "/api/etf/SPY/countries",
        "currentItemCount": 10,
        "totalItems": 10,
        "payload": {
          "symbol": "SPY",
          "countryWeightings": [
            {
              "country": "United States",
              "weightPercentage": 98.5
            },
            {
              "country": "Other",
              "weightPercentage": 1.5
            }
          ]
        }
      }
    }
    ```

    ## Notes:
    - Data is cached for 1 day for performance
    - Particularly useful for international and emerging market ETFs
    - Helps assess geographic diversification and country risk exposure
    - Domestic ETFs (like SPY) will have high concentration in home country
    """
    return await get_etf_country_weightings_controller(symbol=symbol)


@router.post("/etf/info/batch")
async def get_batch_etf_info(request: BatchETFInfoRequest):
    """
    Get ETF information for multiple symbols in a single request.

    ## Overview
    Batch endpoint for fetching ETF metadata for up to 10 ETF symbols at once.
    Uses parallel API calls internally since FMP doesn't have a native batch endpoint.

    ## Rate Limit
    Maximum 10 ETF symbols per request to prevent API rate limiting.

    ## Request Body
    ```json
    {
      "symbols": ["SPY", "QQQ", "VTI", "IWM"]
    }
    ```

    ## Response Format
    ```json
    {
      "status": 200,
      "message": "Batch ETF info retrieved successfully (4 found, 0 not found)",
      "data": {
        "kind": "etf#batchInfo",
        "id": "IWM,QQQ,SPY,VTI",
        "selfLink": "/api/etf/info/batch",
        "currentItemCount": 4,
        "totalItems": 4,
        "payload": {
          "data": {
            "SPY": {
              "symbol": "SPY",
              "name": "SPDR S&P 500 ETF Trust",
              "assetClass": "Large Cap Equity",
              ...
            },
            "QQQ": { ... }
          },
          "missing_symbols": []
        }
      }
    }
    ```

    ## Notes
    - Data is cached for 1 day for performance
    - Invalid/unknown symbols are returned in `missing_symbols` array
    - Symbols are automatically uppercased and deduplicated
    """
    return await get_batch_etf_info_controller(symbols=request.symbols)
