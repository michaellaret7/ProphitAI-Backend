"""
Stress Test Workflow Runner
Runs stress test engine and analysis for all scenarios
"""

import json
import pandas as pd
from backend.src.stress_test.simulated_shocks.engine import run_stress_test_engine
from backend.src.stress_test.simulated_shocks.analysis import (
    industry_returns_analysis,
    contribution_analysis,
    performance_analysis
)
from backend.src.stress_test.simulated_shocks.scenarios import (
    historical_scenarios,
    hypothetical_scenarios
)

def run_stress_test_workflow(portfolio_dict: dict):
    """
    Run stress test workflow for all scenarios.
    
    Parameters:
    - portfolio_dict: Dictionary with tickers as keys and 'conviction'/'position' as values
    
    Returns:
    - dict: Results for all scenarios
    """
    all_results = {}
    
    # Process historical scenarios (remove date fields)
    for scenario_name, scenario_data in historical_scenarios.items():
        # Extract ETF shocks (exclude date fields)
        etf_shocks = {k: v for k, v in scenario_data.items() 
                      if k not in ['start_date', 'end_date']}
        
        # Run stress test engine
        engine_results = run_stress_test_engine(portfolio_dict, etf_shocks)
        
        # Convert to format expected by analysis functions
        scenario_results = _format_engine_results(
            engine_results, 
            portfolio_dict, 
            scenario_name, 
            etf_shocks
        )
        
        # Run analysis functions
        analysis_results = {
            'scenario_name': scenario_name,
            'scenario_type': 'historical',
            'etf_shocks': etf_shocks,
            'stock_returns': engine_results['expected_returns'],
            'industry_returns': industry_returns_analysis(scenario_results, portfolio_dict),
            'contribution': contribution_analysis(scenario_results, portfolio_dict),
            'performance': performance_analysis(scenario_results, portfolio_dict)
        }
        
        all_results[f'historical_{scenario_name}'] = analysis_results
    
    # Process hypothetical scenarios
    for scenario_name, etf_shocks in hypothetical_scenarios.items():
        # Run stress test engine
        engine_results = run_stress_test_engine(portfolio_dict, etf_shocks)
        
        # Convert to format expected by analysis functions
        scenario_results = _format_engine_results(
            engine_results, 
            portfolio_dict, 
            scenario_name, 
            etf_shocks
        )
        
        # Run analysis functions
        analysis_results = {
            'scenario_name': scenario_name,
            'scenario_type': 'hypothetical',
            'etf_shocks': etf_shocks,
            'stock_returns': engine_results['expected_returns'],
            'industry_returns': industry_returns_analysis(scenario_results, portfolio_dict),
            'contribution': contribution_analysis(scenario_results, portfolio_dict),
            'performance': performance_analysis(scenario_results, portfolio_dict)
        }
        
        all_results[f'hypothetical_{scenario_name}'] = analysis_results
    
    return all_results


def _format_engine_results(engine_results, portfolio_dict, scenario_name, etf_shocks):
    """
    Helper function to format engine results for analysis functions.
    
    Parameters:
    - engine_results: Results from run_stress_test_engine
    - portfolio_dict: Portfolio dictionary
    - scenario_name: Name of the scenario
    - etf_shocks: ETF shock values
    
    Returns:
    - dict: Formatted results for analysis functions
    """
    position_details_list = []
    
    for ticker, return_pct in engine_results['expected_returns'].items():
        position = portfolio_dict[ticker]["position"]
        return_decimal = return_pct / 100.0
        pnl = return_decimal if position == "long" else -return_decimal
        
        position_details_list.append({
            'ticker': ticker,
            'position': position,
            'pnl': pnl,
            'total_stock_return': return_decimal,
            # Add beta columns from results
            **{f'beta_{etf}': engine_results['betas'][ticker].get(etf, 0.0) 
               for etf in etf_shocks.keys()}
        })
    
    return {
        'position_details': pd.DataFrame(position_details_list),
        'scenario_name': scenario_name,
        'scenario_etf_moves': etf_shocks
    }


if __name__ == "__main__":
    # Example portfolio for testing
    portfolio_dict = {
        # Long positions
        "CASY": {"conviction": 0.10, "position": "long"},
        "CELH": {"conviction": 0.10, "position": "long"},
        "ODC": {"conviction": 0.05, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.05, "position": "long"},
        "VITL": {"conviction": 0.05, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.05, "position": "long"},
        "COCO": {"conviction": 0.05, "position": "long"},
        "MNST": {"conviction": 0.05, "position": "long"},
        "CL": {"conviction": 0.05, "position": "long"},
        "IPAR": {"conviction": 0.05, "position": "long"},
        "TPB": {"conviction": 0.05, "position": "long"},
        "DOLE": {"conviction": 0.05, "position": "long"},
        "PPC": {"conviction": 0.05, "position": "long"},
        "INGR": {"conviction": 0.05, "position": "long"},
        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.02, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.05, "position": "short"},
        "MGPI": {"conviction": 0.05, "position": "short"},
        "ENR": {"conviction": 0.05, "position": "short"},
        "SPB": {"conviction": 0.05, "position": "short"},
        "COTY": {"conviction": 0.05, "position": "short"},
        "KVUE": {"conviction": 0.05, "position": "short"},
        "KLG": {"conviction": 0.05, "position": "short"},
        "JJSF": {"conviction": 0.05, "position": "short"},
        "SEB": {"conviction": 0.05, "position": "short"}
    }


    from backend.src.utils.token_count import get_token_count
    
    # Run the workflow and return raw results
    results = run_stress_test_workflow(portfolio_dict)
    print(json.dumps(results, indent=4))

    print(get_token_count(results))