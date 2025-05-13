import json
from src.data.PortfolioData import (
    get_portfolio_holdings,
    analyze_portfolio_correlations,
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics,
    analyze_portfolio_diversification,
)
from src.utils.ib_utils import connect_to_ib

# NOTE: The third-party imports below were unused in this module.  They have
# been removed to reduce start-up time and avoid unnecessary dependencies.

def format_to_json():
    active_ib = connect_to_ib()
    positions, formatted_output = get_portfolio_holdings(active_ib, print_output=False)
            
    # Prepare default placeholders so that the later payload build does not
    # raise ``UnboundLocalError`` when the portfolio is empty.
    metrics = None
    monthly_results = None
    diversification = None
    correlations = None
    
    if positions:
        symbols = [p['contract'].symbol for p in positions]
        
        # Calculate portfolio metrics
        metrics = calculate_portfolio_metrics(active_ib, symbols, printOutput=False)
        
        # Calculate monthly portfolio metrics
        monthly_results = calculate_monthly_portfolio_metrics(active_ib, symbols, print_output=False)
        
        # Analyze portfolio diversification
        diversification = analyze_portfolio_diversification(active_ib, print_output=False)
        
        # Analyze portfolio correlations
        correlations = analyze_portfolio_correlations(active_ib, symbols, print_output=False)
    
    # ------------------------------------------------------------------
    # Sanitize *positions* so every entry is JSON-serialisable
    # ------------------------------------------------------------------
    json_positions = []
    if positions:
        for p in positions:
            entry = p.copy()
            contract_obj = entry.pop("contract", None)
            # Remove sensitive or non-serialisable fields
            entry.pop("account", None)
            # Replace contract with its symbol (or string representation)
            if contract_obj is not None:
                entry["symbol"] = str(getattr(contract_obj, "symbol", contract_obj))
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

    # We intentionally delay ``disconnect`` until after the conditional so
    # that it is invoked exactly once, regardless of whether we entered
    # the *positions* block or not.

    # Always close the Interactive Brokers connection that we opened earlier
    active_ib.disconnect()

    return json_block

