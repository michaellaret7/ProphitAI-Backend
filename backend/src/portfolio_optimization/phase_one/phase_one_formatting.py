import json
from backend.src.utils.database import get_cursor
from typing import List, Dict, Any, Optional
from backend.src.data.PortfolioData import (
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics,
    analyze_portfolio_correlations
)
from backend.src.utils.retrieve_portfolio_from_db import retrieve_user_current_portfolio_from_db


def get_holdings_from_database(user_id: str, email: str) -> tuple[List[Dict[str, Any]], str]:
    """
    Retrieve holdings from the database using user_id and email.
    
    Queries the user_portfolios table to fetch the most recent holdings
    for the specified user with proper data type conversion.
    
    Args:
        user_id: The user ID of the user whose holdings to retrieve.
        email: The email of the user whose holdings to retrieve.
        
    Returns:
        Tuple[List[Dict[str, Any]], str]: Tuple containing list of position dictionaries 
        and formatted status string, or empty list and error message if failed.
    """
    try:
        # Use the new utility function to get the portfolio as a DataFrame
        portfolio_df = retrieve_user_current_portfolio_from_db(user_id=user_id, email=email)

        if portfolio_df is None or portfolio_df.empty:
            return [], f"No positions found in database for user_id: {user_id} or email: {email}."

        # Sort by timestamp to get the most recent for each symbol and account, then drop duplicates
        portfolio_df = portfolio_df.sort_values('fetch_timestamp', ascending=False).drop_duplicates(subset=['symbol', 'account'])
        
        # Format positions to match the expected structure
        positions = []
        for _, row in portfolio_df.iterrows():
            position = {
                'symbol': row.get('symbol'),
                'secType': row.get('secType'),
                'currency': row.get('currency'),
                'position': float(row.get('position', 0.0) or 0.0),
                'marketPrice': float(row.get('marketPrice', 0.0) or 0.0),
                'marketValue': float(row.get('marketValue', 0.0) or 0.0),
                'averageCost': float(row.get('averageCost', 0.0) or 0.0),
                'unrealizedPNL': float(row.get('unrealizedPNL', 0.0) or 0.0),
                'realizedPNL': float(row.get('realizedPNL', 0.0) or 0.0),
                'account': row.get('account')
            }
            positions.append(position)
        
        # Format output string for display
        formatted_output = f"Retrieved {len(positions)} positions from database for user_id: {user_id}"
        
        return positions, formatted_output
            
    except Exception as e:
        print(f"Error retrieving holdings from database: {e}")
        return [], f"Error retrieving holdings: {str(e)}"

def format_to_json(user_id: str, email: str):
    """
    Format comprehensive portfolio data into JSON for Phase One analysis.
    
    Retrieves holdings from database, calculates portfolio metrics, monthly performance,
    correlations, and formats everything into a JSON structure for LLM consumption.
    
    Args:
        user_id (str): The user ID to fetch data for.
        email (str): The user's email to fetch data for.
        
    Returns:
        str: JSON string containing comprehensive portfolio data including positions,
        metrics, performance, and correlations with rounded numeric values.
    """
    # Get holdings from database instead of IBKR
    positions, formatted_output = get_holdings_from_database(user_id=user_id, email=email)
            
    # Prepare default placeholders so that the later payload build does not
    # raise ``UnboundLocalError`` when the portfolio is empty.
    metrics = None
    monthly_results = None
    diversification = None
    correlations = None
    
    if positions:
        symbols = [p['symbol'] for p in positions]
        
        # Now these calculations work with database data
        # Pass None for the IB connection parameter
        
        # Calculate portfolio metrics
        metrics = calculate_portfolio_metrics(None, symbols, printOutput=False)
        
        # Calculate monthly portfolio metrics
        monthly_results = calculate_monthly_portfolio_metrics(None, symbols, print_output=False)
        
        # Analyze portfolio diversification - requires IBKR for contract details
        # diversification = analyze_portfolio_diversification(None, print_output=False)
        
        # Analyze portfolio correlations
        correlations = analyze_portfolio_correlations(None, symbols, print_output=False)
    
    # ------------------------------------------------------------------
    # Sanitize *positions* so every entry is JSON-serialisable
    # ------------------------------------------------------------------
    json_positions = []
    if positions:
        for p in positions:
            entry = p.copy()
            # Remove sensitive or non-serialisable fields
            entry.pop("account", None)
            json_positions.append(entry)

    # Prepare monthly performance data, extracting only the monthly breakdown
    # monthly_results is a dict: {'overall_metrics': {...}, 'monthly_metrics': {...}} or None
    actual_monthly_breakdown = {}
    if monthly_results and isinstance(monthly_results, dict) and 'monthly_metrics' in monthly_results:
        actual_monthly_breakdown = monthly_results['monthly_metrics']

    payload = {
        "portfolio_positions": json_positions,
        "portfolio_risk_metrics": metrics if metrics else {},
        "portfolio_monthly_performance": actual_monthly_breakdown,
        "portfolio_diversification": diversification if diversification else {},
        "portfolio_correlations": correlations.to_dict() if correlations is not None else {},
    }

    # ------------------------------------------------------------------
    # Round all numeric values to 3 decimal places for compact JSON output
    # ------------------------------------------------------------------
    def _round(obj, decimals: int = 3):
        """Recursively round floats in nested structures."""
        if isinstance(obj, float):
            return round(obj, decimals)
        if isinstance(obj, dict):
            return {k: _round(v, decimals) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_round(v, decimals) for v in obj]
        return obj

    payload = _round(payload)

    json_block = json.dumps(payload)
    # print(json_block)

    return json_block

