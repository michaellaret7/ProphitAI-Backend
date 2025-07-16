from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from backend.src.utils.database import get_cursor
import psycopg2
from pydantic import BaseModel
import pandas as pd
from datetime import datetime, timedelta
from backend.src.auth import get_current_user
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.db.core.market_data_models import *
from backend.src.db.core.user_data_models import *
from backend.src.repositories.portfolio_data import retrieve_portfolio 

router = APIRouter()

SPECIFIC_SECTOR_COLORS = {
    "Equity Sector Information Technology": "#5b4cdb", 
    "Energy Focused Etfs": "#f59e0b",
    "Precious Metals Etfs": "#d1a11e", # Gold-ish
    "Cash": "#6b7280", # Grey for cash is often fine
    "Health Care Equipment And Supplies": "#8b5cf6",
    "Broad Based Emerging Market Equity Etfs": "#06b6d4",
    "Consumer Staples Distribution And Retail": "#ec4899",
    # Add more high-priority asset classes here
}

# 2. A larger list of distinct colors to cycle through for other asset classes
FALLBACK_COLORS = [
    "#34d399", # Emerald
    "#ef4444", # Red
    "#3b82f6", # Blue
    "#a855f7", # Purple
    "#eab308", # Amber
    "#10b981", # Teal
    "#f97316", # Orange
    "#6366f1", # Indigo
    "#d946ef", # Fuchsia
    "#84cc16", # Lime
    "#0ea5e9", # Sky
    "#14b8a6", # Cyan
]

DEFAULT_UNASSIGNED_COLOR = "#9ca3af" # A neutral default if all fallbacks are used

# Pydantic model for individual holding
class HoldingBase(BaseModel):
    symbol: str
    quantity: float
    currentPrice: float
    marketValue: float
    pnl: float
    pnlPercent: float
    portfolioPercent: float # This will be calculated after fetching all holdings

# Pydantic model for the response
class PortfolioHoldingsResponse(BaseModel):
    holdings: List[HoldingBase]

# Pydantic model for portfolio performance data point
class PerformanceDataPoint(BaseModel):
    date: str
    value: float
    dailyReturn: float
    cumulativeReturn: float
    portfolio_normalized: Optional[float] = None
    spy_normalized: Optional[float] = None
    portfolio_return: Optional[float] = None
    spy_return: Optional[float] = None
    qqq_normalized: Optional[float] = None
    qqq_return: Optional[float] = None
    iwm_normalized: Optional[float] = None
    iwm_return: Optional[float] = None
    gld_normalized: Optional[float] = None
    gld_return: Optional[float] = None
    dbc_normalized: Optional[float] = None
    dbc_return: Optional[float] = None
    eem_normalized: Optional[float] = None
    eem_return: Optional[float] = None

# Pydantic model for portfolio performance response
class PortfolioPerformanceResponse(BaseModel):
    performanceData: List[PerformanceDataPoint]
    totalReturn: float
    startDate: str
    endDate: str
    spyTotalReturn: Optional[float] = None
    qqqTotalReturn: Optional[float] = None
    iwmTotalReturn: Optional[float] = None
    gldTotalReturn: Optional[float] = None
    dbcTotalReturn: Optional[float] = None
    eemTotalReturn: Optional[float] = None

#THIS RETRIEVES THE SECTOR ALLOCATIONS FOR THE OPTIMIZED/BUILT PORTFOLIOS
@router.get("/portfolio/allocation")
async def get_portfolio_allocation(current_user=Depends(get_current_user)):
    """
    Retrieve all portfolio sector allocations for the currently authenticated user.
    
    Queries the portfolio_sector_allocation table for the given user_id
    and returns all associated sector allocations.
    
    Args:
        current_user: The authenticated user object, injected by dependency.
        
    Returns:
        Dict containing sectors array with allocation data.
        
    Raises:
        HTTPException: 404 if no allocation data is found for the user,
                      401 if user is not authenticated,
                      500 if database query fails.
    """
    
    user_id = current_user.id
    email = current_user.email
    portfolio_id = "b0914b3f-a203-47e5-b602-af0a28d824f0" # As requested

    try:
        # Use the existing function to get portfolio allocations
        allocations_df = retrieve_portfolio(portfolio_id=portfolio_id, email=email)
        
        # The function returns None on DB error, or an empty DataFrame if no records found.
        if allocations_df is None:
            raise HTTPException(status_code=500, detail="Database error processing portfolio allocation.")

        if allocations_df.empty:
            raise HTTPException(status_code=404, detail="No allocation data found for the current user.")
            
        # Filter for allocations > 0 and sort
        allocations_df = allocations_df[allocations_df['allocation'] > 0]
        allocations_df = allocations_df.sort_values(by='allocation', ascending=False)

        # Process data
        final_sectors = []
        assigned_fallback_colors = 0
        
        for _, row in allocations_df.iterrows():
            asset_class = row['asset_class']
            allocation_value_from_db = row['allocation']
            
            sector_name_formatted = str(asset_class).replace('_', ' ').title()
            allocation_percent = float(allocation_value_from_db)
            
            color = DEFAULT_UNASSIGNED_COLOR # Start with a base default

            # Check specific overrides first
            if sector_name_formatted in SPECIFIC_SECTOR_COLORS:
                color = SPECIFIC_SECTOR_COLORS[sector_name_formatted]
            elif asset_class in SPECIFIC_SECTOR_COLORS: # Check raw asset_class too
                 color = SPECIFIC_SECTOR_COLORS[asset_class]
            else:
                # Cycle through fallback colors for unassigned sectors
                if assigned_fallback_colors < len(FALLBACK_COLORS):
                    color = FALLBACK_COLORS[assigned_fallback_colors]
                    assigned_fallback_colors += 1
                # If more sectors than fallback colors, they'll get DEFAULT_UNASSIGNED_COLOR
                
            final_sectors.append({
                "name": sector_name_formatted,
                "percentage": round(allocation_percent, 2),
                "color": color,
            })
        
        return {"sectors": final_sectors}
        
    except HTTPException:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise
    except Exception as e:
        print(f"Unexpected error for user_id {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing portfolio allocation.")

# THIS RETRIEVES THE HOLDINGS FOR THE USERS CURRENT PORTFOLIO
@router.get("/portfolio/holdings", response_model=PortfolioHoldingsResponse)
async def get_current_user_holdings(current_user=Depends(get_current_user)):
    """
    Retrieve portfolio holdings data for the currently authenticated user.
    
    Queries the user_portfolios table to fetch all stock holdings for the logged-in user,
    including position sizes, current prices, market values, and P&L calculations.
        
    Returns:
        PortfolioHoldingsResponse: Object containing list of holdings with market values and percentages.
        
    Raises:
        HTTPException: 500 error if database query fails or 401 if user is not authenticated.
    """
    user_id = current_user.id 
    email = current_user.email
    portfolio_id = "b0914b3f-a203-47e5-b602-af0a28d824f0" # As requested

    try:
        holdings_df = retrieve_portfolio(portfolio_id=portfolio_id, email=email)

        if holdings_df is None:
            raise HTTPException(status_code=500, detail="Database error retrieving portfolio holdings.")

        if holdings_df.empty:
            return PortfolioHoldingsResponse(holdings=[])

        # Filter for STK security type, which was part of the original query
        holdings_df = holdings_df[holdings_df['sectype'] == 'STK']
        
        if holdings_df.empty:
            return PortfolioHoldingsResponse(holdings=[])

        holdings_data = []
        total_portfolio_value = 0.0

        for _, row in holdings_df.iterrows():
            # Ensure correct column names from the dataframe
            symbol = row['symbol']
            quantity = row['position']
            current_price = row['marketprice']
            market_value = row['marketvalue']
            unrealized_pnl = row['unrealizedpnl']
            
            quantity = float(quantity) if quantity is not None else 0.0
            current_price = float(current_price) if current_price is not None else 0.0
            market_value = float(market_value) if market_value is not None else 0.0
            unrealized_pnl = float(unrealized_pnl) if unrealized_pnl is not None else 0.0

            cost_basis = market_value - unrealized_pnl
            pnl_percent = (unrealized_pnl / cost_basis) * 100 if cost_basis != 0 else 0.0
            
            holdings_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "currentPrice": current_price,
                "marketValue": market_value,
                "pnl": unrealized_pnl,
                "pnlPercent": round(pnl_percent, 2),
                # portfolioPercent will be calculated in the next loop
            })
            total_portfolio_value += market_value
        
        final_holdings = []
        if total_portfolio_value > 0:
            for holding in holdings_data:
                portfolio_percent = (holding["marketValue"] / total_portfolio_value) * 100
                final_holdings.append(HoldingBase(
                    **holding,
                    portfolioPercent=round(portfolio_percent, 2)
                ))
        else: 
             for holding in holdings_data:
                final_holdings.append(HoldingBase(
                    **holding,
                    portfolioPercent=0.0
                ))

        return PortfolioHoldingsResponse(holdings=final_holdings)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error for user_id {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error retrieving portfolio holdings.") 

# THIS RETRIEVES THE PERFORMANCE FOR THE USERS CURRENT PORTFOLIO FROM THEIR BROKER
@router.get("/portfolio/performance", response_model=PortfolioPerformanceResponse)
async def get_portfolio_performance(days: int = 365, current_user=Depends(get_current_user)):
    """
    Calculate and retrieve historical portfolio performance metrics for a user.
    
    Fetches user holdings, retrieves historical price data for each position,
    calculates portfolio values over time, and compares performance against
    multiple benchmark ETFs (SPY, QQQ, IWM, GLD, DBC, EEM).
    
    Args:
        days: Number of days of historical data to retrieve (default: 365)
        current_user: The authenticated user object, injected by dependency.
        
    Returns:
        PortfolioPerformanceResponse: Object containing performance data with values, 
        daily/cumulative returns, normalized values for comparison, and total returns.
        
    Raises:
        HTTPException: 404 if no holdings found or no price data available,
                      500 if database query or calculation fails.
    """
    
    db_name = "user_data"
    schema_name = "public"
    table_name = "user_portfolios"
    user_id = current_user.id
    
    try:
        # Step 1: Get the user's current portfolio holdings
        query = psycopg2.sql.SQL("""
            SELECT symbol, position, marketvalue, averagecost
            FROM {}.{}
            WHERE user_id = %s AND sectype = 'STK' AND position > 0
        """).format(psycopg2.sql.Identifier(schema_name), psycopg2.sql.Identifier(table_name))
        
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, (user_id,))
            holdings = cursor.fetchall()
            
            if not holdings:
                raise HTTPException(status_code=404, detail=f"No holdings found for the current user.")
        
        # Step 2: Calculate date range
        # current_date = datetime.now()
        # end_date = current_date - timedelta(days=1) # Modified end_date to keep up with the data. This will be used in live program
        end_date = datetime(2025, 6, 1) # this is a test just because we are in dev and cant keep updating the data every morning. Not a permanent solution.
        start_date = end_date - timedelta(days=days)
        
        # Step 3: Get price data for each holding and SPY
        portfolio_data = []
        for symbol, position, market_value, avg_cost in holdings:
            position = float(position) if position else 0.0
            
            # Get price data for this symbol
            price_data = get_price_data_daily(
                ticker=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if price_data is not None and not price_data.empty:
                # Add position and symbol to the dataframe
                price_data['symbol'] = symbol
                price_data['position'] = position
                price_data['value'] = price_data['close'] * position
                portfolio_data.append(price_data)
        
        # Step 3.5: Get SPY price data for comparison
        spy_data = get_price_data_daily(
            ticker='SPY',
            start_date=start_date,
            end_date=end_date
        )
        
        # Get additional ETF data
        qqq_data = get_price_data_daily(
            ticker='QQQ',
            start_date=start_date,
            end_date=end_date
        )
        
        iwm_data = get_price_data_daily(
            ticker='IWM',
            start_date=start_date,
            end_date=end_date
        )
        
        # Get additional new ETF data
        gld_data = get_price_data_daily(
            ticker='GLD',
            start_date=start_date,
            end_date=end_date
        )
        
        dbc_data = get_price_data_daily(
            ticker='DBC',
            start_date=start_date,
            end_date=end_date
        )
        
        eem_data = get_price_data_daily(
            ticker='EEM',
            start_date=start_date,
            end_date=end_date
        )
        
        if not portfolio_data:
            raise HTTPException(status_code=404, detail="No price data available for portfolio holdings")
        
        # Step 4: Combine all holdings data
        combined_df = pd.concat(portfolio_data, ignore_index=True)
        
        # Step 5: Calculate portfolio value by date
        portfolio_values = combined_df.groupby('date')['value'].sum().reset_index()
        portfolio_values = portfolio_values.sort_values('date')

        if not portfolio_values.empty:
            # Ensure 'date' column is datetime for comparison; it typically is already.
            portfolio_values['date'] = pd.to_datetime(portfolio_values['date'])
            # Filter out any data that is strictly after the date part of our calculated 'end_date'
            portfolio_values = portfolio_values[portfolio_values['date'].dt.date <= end_date.date()]

        if portfolio_values.empty: # Check if filtering left no data
            # Use end_date.date() for formatting the message, as it's the actual cutoff.
            raise HTTPException(status_code=404, detail=f"No performance data available up to {end_date.date().strftime('%Y-%m-%d')}")
        
        # Step 6: Normalize portfolio and all ETFs to start at 100 for comparison
        final_data = portfolio_values.copy()
        
        # Start with portfolio normalization
        if len(final_data) > 0:
            initial_portfolio_value = final_data['value'].iloc[0]
            final_data['portfolio_normalized'] = (final_data['value'] / initial_portfolio_value) * 100
            final_data['portfolio_return'] = ((final_data['portfolio_normalized'] / 100) - 1) * 100
            
            # Merge and normalize SPY
            if spy_data is not None and not spy_data.empty:
                spy_data = spy_data.rename(columns={'close': 'spy_close'})
                final_data = pd.merge(final_data, spy_data[['date', 'spy_close']], on='date', how='left')
                if 'spy_close' in final_data.columns and not final_data['spy_close'].isna().all():
                    first_valid_spy = final_data['spy_close'].first_valid_index()
                    if first_valid_spy is not None:
                        initial_spy_value = final_data.loc[first_valid_spy, 'spy_close']
                        final_data['spy_normalized'] = (final_data['spy_close'] / initial_spy_value) * 100
                        final_data['spy_return'] = ((final_data['spy_normalized'] / 100) - 1) * 100
                    else:
                        final_data['spy_normalized'] = None
                        final_data['spy_return'] = None
                else:
                    final_data['spy_normalized'] = None
                    final_data['spy_return'] = None
            
            # Merge and normalize QQQ
            if qqq_data is not None and not qqq_data.empty:
                qqq_data = qqq_data.rename(columns={'close': 'qqq_close'})
                final_data = pd.merge(final_data, qqq_data[['date', 'qqq_close']], on='date', how='left')
                if 'qqq_close' in final_data.columns and not final_data['qqq_close'].isna().all():
                    first_valid_qqq = final_data['qqq_close'].first_valid_index()
                    if first_valid_qqq is not None:
                        initial_qqq_value = final_data.loc[first_valid_qqq, 'qqq_close']
                        final_data['qqq_normalized'] = (final_data['qqq_close'] / initial_qqq_value) * 100
                        final_data['qqq_return'] = ((final_data['qqq_normalized'] / 100) - 1) * 100
                    else:
                        final_data['qqq_normalized'] = None
                        final_data['qqq_return'] = None
                else:
                    final_data['qqq_normalized'] = None
                    final_data['qqq_return'] = None
            
            # Merge and normalize IWM
            if iwm_data is not None and not iwm_data.empty:
                iwm_data = iwm_data.rename(columns={'close': 'iwm_close'})
                final_data = pd.merge(final_data, iwm_data[['date', 'iwm_close']], on='date', how='left')
                if 'iwm_close' in final_data.columns and not final_data['iwm_close'].isna().all():
                    first_valid_iwm = final_data['iwm_close'].first_valid_index()
                    if first_valid_iwm is not None:
                        initial_iwm_value = final_data.loc[first_valid_iwm, 'iwm_close']
                        final_data['iwm_normalized'] = (final_data['iwm_close'] / initial_iwm_value) * 100
                        final_data['iwm_return'] = ((final_data['iwm_normalized'] / 100) - 1) * 100
                    else:
                        final_data['iwm_normalized'] = None
                        final_data['iwm_return'] = None
                else:
                    final_data['iwm_normalized'] = None
                    final_data['iwm_return'] = None
            
            # Merge and normalize GLD
            if gld_data is not None and not gld_data.empty:
                gld_data = gld_data.rename(columns={'close': 'gld_close'})
                final_data = pd.merge(final_data, gld_data[['date', 'gld_close']], on='date', how='left')
                if 'gld_close' in final_data.columns and not final_data['gld_close'].isna().all():
                    first_valid_gld = final_data['gld_close'].first_valid_index()
                    if first_valid_gld is not None:
                        initial_gld_value = final_data.loc[first_valid_gld, 'gld_close']
                        final_data['gld_normalized'] = (final_data['gld_close'] / initial_gld_value) * 100
                        final_data['gld_return'] = ((final_data['gld_normalized'] / 100) - 1) * 100
                    else:
                        final_data['gld_normalized'] = None
                        final_data['gld_return'] = None
                else:
                    final_data['gld_normalized'] = None
                    final_data['gld_return'] = None
            
            # Merge and normalize DBC
            if dbc_data is not None and not dbc_data.empty:
                dbc_data = dbc_data.rename(columns={'close': 'dbc_close'})
                final_data = pd.merge(final_data, dbc_data[['date', 'dbc_close']], on='date', how='left')
                if 'dbc_close' in final_data.columns and not final_data['dbc_close'].isna().all():
                    first_valid_dbc = final_data['dbc_close'].first_valid_index()
                    if first_valid_dbc is not None:
                        initial_dbc_value = final_data.loc[first_valid_dbc, 'dbc_close']
                        final_data['dbc_normalized'] = (final_data['dbc_close'] / initial_dbc_value) * 100
                        final_data['dbc_return'] = ((final_data['dbc_normalized'] / 100) - 1) * 100
                    else:
                        final_data['dbc_normalized'] = None
                        final_data['dbc_return'] = None
                else:
                    final_data['dbc_normalized'] = None
                    final_data['dbc_return'] = None
            
            # Merge and normalize EEM
            if eem_data is not None and not eem_data.empty:
                eem_data = eem_data.rename(columns={'close': 'eem_close'})
                final_data = pd.merge(final_data, eem_data[['date', 'eem_close']], on='date', how='left')
                if 'eem_close' in final_data.columns and not final_data['eem_close'].isna().all():
                    first_valid_eem = final_data['eem_close'].first_valid_index()
                    if first_valid_eem is not None:
                        initial_eem_value = final_data.loc[first_valid_eem, 'eem_close']
                        final_data['eem_normalized'] = (final_data['eem_close'] / initial_eem_value) * 100
                        final_data['eem_return'] = ((final_data['eem_normalized'] / 100) - 1) * 100
                    else:
                        final_data['eem_normalized'] = None
                        final_data['eem_return'] = None
                else:
                    final_data['eem_normalized'] = None
                    final_data['eem_return'] = None
        else:
            # No data case
            final_data['portfolio_normalized'] = 100
            final_data['spy_normalized'] = None
            final_data['qqq_normalized'] = None
            final_data['iwm_normalized'] = None
            final_data['gld_normalized'] = None
            final_data['dbc_normalized'] = None
            final_data['eem_normalized'] = None
            final_data['portfolio_return'] = 0
            final_data['spy_return'] = None
            final_data['qqq_return'] = None
            final_data['iwm_return'] = None
            final_data['gld_return'] = None
            final_data['dbc_return'] = None
            final_data['eem_return'] = None

        # Step 7: Calculate daily returns
        final_data['dailyReturn'] = final_data['value'].pct_change().fillna(0)
        final_data['cumulativeReturn'] = (1 + final_data['dailyReturn']).cumprod() - 1
        
        # Step 8: Format response with both portfolio and SPY data
        performance_data = []
        for _, row in final_data.iterrows():
            # Create base data point
            data_point_dict = {
                'date': row['date'].strftime('%Y-%m-%d'),
                'value': round(row['value'], 2),
                'dailyReturn': round(row['dailyReturn'] * 100, 4),
                'cumulativeReturn': round(row['cumulativeReturn'] * 100, 2),
                'portfolio_normalized': round(row['portfolio_normalized'], 2) if pd.notna(row['portfolio_normalized']) else None,
                'portfolio_return': round(row['portfolio_return'], 2) if pd.notna(row['portfolio_return']) else None,
                'spy_normalized': round(row['spy_normalized'], 2) if pd.notna(row['spy_normalized']) else None,
                'spy_return': round(row['spy_return'], 2) if pd.notna(row['spy_return']) else None,
                'qqq_normalized': round(row['qqq_normalized'], 2) if pd.notna(row['qqq_normalized']) else None,
                'qqq_return': round(row['qqq_return'], 2) if pd.notna(row['qqq_return']) else None,
                'iwm_normalized': round(row['iwm_normalized'], 2) if pd.notna(row['iwm_normalized']) else None,
                'iwm_return': round(row['iwm_return'], 2) if pd.notna(row['iwm_return']) else None,
                'gld_normalized': round(row['gld_normalized'], 2) if pd.notna(row['gld_normalized']) else None,
                'gld_return': round(row['gld_return'], 2) if pd.notna(row['gld_return']) else None,
                'dbc_normalized': round(row['dbc_normalized'], 2) if pd.notna(row['dbc_normalized']) else None,
                'dbc_return': round(row['dbc_return'], 2) if pd.notna(row['dbc_return']) else None,
                'eem_normalized': round(row['eem_normalized'], 2) if pd.notna(row['eem_normalized']) else None,
                'eem_return': round(row['eem_return'], 2) if pd.notna(row['eem_return']) else None,
            }
            
            performance_data.append(data_point_dict)
        
        # Calculate total returns
        if len(final_data) > 1:
            total_return = float(final_data['cumulativeReturn'].iloc[-1] * 100)
            portfolio_total_return = float(final_data['portfolio_return'].iloc[-1]) if 'portfolio_return' in final_data.columns else total_return
            spy_total_return = float(final_data['spy_return'].iloc[-1]) if 'spy_return' in final_data.columns and pd.notna(final_data['spy_return'].iloc[-1]) else None
            qqq_total_return = float(final_data['qqq_return'].iloc[-1]) if 'qqq_return' in final_data.columns and pd.notna(final_data['qqq_return'].iloc[-1]) else None
            iwm_total_return = float(final_data['iwm_return'].iloc[-1]) if 'iwm_return' in final_data.columns and pd.notna(final_data['iwm_return'].iloc[-1]) else None
            gld_total_return = float(final_data['gld_return'].iloc[-1]) if 'gld_return' in final_data.columns and pd.notna(final_data['gld_return'].iloc[-1]) else None
            dbc_total_return = float(final_data['dbc_return'].iloc[-1]) if 'dbc_return' in final_data.columns and pd.notna(final_data['dbc_return'].iloc[-1]) else None
            eem_total_return = float(final_data['eem_return'].iloc[-1]) if 'eem_return' in final_data.columns and pd.notna(final_data['eem_return'].iloc[-1]) else None
        else:
            total_return = 0.0
            portfolio_total_return = 0.0
            spy_total_return = None
            qqq_total_return = None
            iwm_total_return = None
            gld_total_return = None
            dbc_total_return = None
            eem_total_return = None
        
        response_dict = {
            "performanceData": performance_data,
            "totalReturn": round(portfolio_total_return, 2),
            "startDate": final_data['date'].iloc[0].strftime('%Y-%m-%d') if len(final_data) > 0 else "",
            "endDate": final_data['date'].iloc[-1].strftime('%Y-%m-%d') if len(final_data) > 0 else "",
            "spyTotalReturn": round(spy_total_return, 2) if spy_total_return is not None else None,
            "qqqTotalReturn": round(qqq_total_return, 2) if qqq_total_return is not None else None,
            "iwmTotalReturn": round(iwm_total_return, 2) if iwm_total_return is not None else None,
            "gldTotalReturn": round(gld_total_return, 2) if gld_total_return is not None else None,
            "dbcTotalReturn": round(dbc_total_return, 2) if dbc_total_return is not None else None,
            "eemTotalReturn": round(eem_total_return, 2) if eem_total_return is not None else None,
        }
        
        return response_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting portfolio performance for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error retrieving portfolio performance.") 