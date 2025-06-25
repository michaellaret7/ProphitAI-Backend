import json
from typing import List, Dict, Any, Optional
from backend.src.utils.logging_config import init_logger
from backend.src.utils.portfolio_analysis import (
    _fetch_price_data_for_analysis,
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics,
    analyze_portfolio_correlations,
    get_portfolio_holdings
)
from backend.src.repositories.user.user_portfolio_repository import UserCurrentPortfolioRepository
from backend.src.utils.logging_config import init_logger

logger = init_logger(__name__)

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
    portfolio_df = UserCurrentPortfolioRepository().fetch_holdings(user_id=user_id, email=email)
    logger.info(f"Retrieved {len(portfolio_df)} positions from database for user_id: {user_id} or email: {email}.")
    positions = portfolio_df
    formatted_output = f"Retrieved {len(positions)} positions from database for user_id: {user_id}"

    metrics = None
    monthly_results = None
    diversification = None
    correlations = None
    
    if positions:
        symbols = [p.symbol for p in positions]
        
        # Fetch all price data once
        prices_df, market_prices = _fetch_price_data_for_analysis(symbols, years=2.0)
        
        # Reformat positions to be compatible with analysis functions
        # This is temporary until all parts of the codebase use the same data models
        formatted_positions = get_portfolio_holdings(user_id=user_id, email=email)

        if prices_df is not None and not prices_df.empty:
            # Calculate portfolio metrics
            metrics = calculate_portfolio_metrics(prices_df, market_prices, formatted_positions)
            
            # Calculate monthly portfolio metrics
            monthly_results = calculate_monthly_portfolio_metrics(prices_df, market_prices, formatted_positions)
            
            # Analyze portfolio correlations
            correlations = analyze_portfolio_correlations(prices_df)
    
    # ------------------------------------------------------------------
    # Sanitize *positions* so every entry is JSON-serialisable
    # ------------------------------------------------------------------
    json_positions = []
    if positions:
        total_market_value = sum(p.marketvalue for p in positions)
        for p in positions:
            portfolio_percentage = (p.marketvalue / total_market_value) * 100 if total_market_value > 0 else 0
            entry = {
                "symbol": p.symbol,
                "quantity": p.position,
                "average_cost": p.averagecost,
                "market_price": p.marketprice,
                "market_value": p.marketvalue,
                "unrealized_pnl": p.unrealizedpnl,
                "realized_pnl": p.realizedpnl,
                "portfolio_percentage": portfolio_percentage,
                "asset_class": p.sectype,
                "updated_at": p.fetch_timestamp.isoformat() if p.fetch_timestamp else None
            }
            json_positions.append(entry)


    actual_monthly_breakdown = {}
    if monthly_results:
        actual_monthly_breakdown = monthly_results

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

    return json_block

if __name__ == "__main__":
    logger.info(format_to_json(user_id="user_01JXG39MMAVW1P3XVGX7YHN2DT", email="michael@laret.com"))