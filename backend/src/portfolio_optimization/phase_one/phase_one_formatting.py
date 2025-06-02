import json
from backend.src.utils.database import get_cursor
from typing import List, Dict, Any, Optional
from backend.src.data.PortfolioData import (
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics,
    analyze_portfolio_correlations
)


def get_holdings_from_database(user_name: str = "test_user_beta_one") -> tuple[List[Dict[str, Any]], str]:
    """
    Retrieve holdings from the database instead of IBKR.
    
    Args:
        user_name: Name of the user whose holdings to retrieve
        
    Returns:
        A tuple containing (positions list, formatted string)
    """
    try:
        with get_cursor(dbname='user_data') as cursor:
            # Get the most recent holdings for the user
            query = """
            SELECT DISTINCT ON (symbol, account)
                symbol, secType, currency, position, marketPrice, marketValue,
                averageCost, unrealizedPNL, realizedPNL, account
            FROM public.user_portfolios
            WHERE user_name = %s
            ORDER BY symbol, account, fetch_timestamp DESC
            """
            cursor.execute(query, (user_name,))
            results = cursor.fetchall()
            
            if not results:
                return [], "No positions found in database."
            
            # Format positions to match the expected structure
            positions = []
            for row in results:
                position = {
                    'symbol': row[0],
                    'secType': row[1],
                    'currency': row[2],
                    'position': float(row[3]) if row[3] else 0.0,
                    'marketPrice': float(row[4]) if row[4] else 0.0,
                    'marketValue': float(row[5]) if row[5] else 0.0,
                    'averageCost': float(row[6]) if row[6] else 0.0,
                    'unrealizedPNL': float(row[7]) if row[7] else 0.0,
                    'realizedPNL': float(row[8]) if row[8] else 0.0,
                    'account': row[9]
                }
                positions.append(position)
            
            # Format output string for display
            formatted_output = f"Retrieved {len(positions)} positions from database for user: {user_name}"
            
            return positions, formatted_output
            
    except Exception as e:
        print(f"Error retrieving holdings from database: {e}")
        return [], f"Error retrieving holdings: {str(e)}"

def format_to_json():
    # Get holdings from database instead of IBKR
    positions, formatted_output = get_holdings_from_database()
            
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

