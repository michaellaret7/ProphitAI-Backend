import json
from src.data.PortfolioData import get_portfolio_holdings, analyze_portfolio_correlations, calculate_portfolio_metrics, calculate_monthly_portfolio_metrics, calculate_monthly_stock_metrics, analyze_portfolio_diversification, analyze_portfolio_correlations
from src.utils.ib_utils import connect_to_ib, disconnect_from_ib, get_ib
from openai import OpenAI
import numpy as np
import os
from datetime import datetime
import pandas as pd


def format_to_json():
    active_ib = connect_to_ib()
    positions, formatted_output = get_portfolio_holdings(active_ib, print_output=False)
            
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
        
        # Mark data as fetched to avoid duplicate calls
        _data_fetched = True
        
        # Close the connection if we created it here
        active_ib.disconnect()
    
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

    def _default(o):
        """Fallback JSON serializer that converts unknown objects to string."""
        return str(o)

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
    print(json_block)

    return json_block

