"""
Stress Test Workflow Runner
Runs stress test engine and analysis for all scenarios with optimized data fetching
"""

import json
import pandas as pd
from backend.src.stress_test.engine import (
    run_stress_test_engine,
    get_portfolio_betas
)
from backend.src.stress_test.performance_analysis import (
    industry_returns_analysis,
    contribution_analysis,
    performance_analysis
)
from backend.src.stress_test.scenarios import (
    historical_scenarios,
    hypothetical_scenarios
)

from backend.src.stress_test.pairwise_corr_analysis import (
    run_pairwise_correlation_analysis
)


class StressTestRunner:
    """
    Optimized stress test runner that caches betas to avoid redundant data fetching.
    Pairwise correlation analysis is computed lazily and only for historical scenarios.
    """
    
    def __init__(self, portfolio_dict: dict):
        """
        Initialize the stress test runner with a portfolio.
        Fetches all required data once during initialization.
        
        Parameters:
        - portfolio_dict: Dictionary with tickers as keys and 'conviction'/'position' as values
        """
        self.portfolio_dict = portfolio_dict
        self.tickers = list(portfolio_dict.keys())
        
        # Get all unique ETFs from scenarios
        self.etf_list = self._get_all_etfs()
        
        # Fetch betas once for all ETFs
        print(f"Fetching betas for {len(self.tickers)} tickers and {len(self.etf_list)} ETFs...")
        self.cached_betas = get_portfolio_betas(
            self.tickers,
            {etf: 0 for etf in self.etf_list}  # Dummy shocks just to get betas
        )
        print("Betas cached successfully.")
        
        # Initialize pairwise correlation cache (lazy loading)
        self._pairwise_corr_analysis = None
    
    def _get_all_etfs(self):
        """
        Extract all unique ETFs from both historical and hypothetical scenarios.
        """
        etf_set = set()
        
        # Extract ETFs from historical scenarios
        for scenario_data in historical_scenarios.values():
            etf_set.update(
                k for k in scenario_data.keys() 
                if k not in ['start_date', 'end_date']
            )
        
        # Extract ETFs from hypothetical scenarios
        for etf_shocks in hypothetical_scenarios.values():
            etf_set.update(etf_shocks.keys())
        
        return list(etf_set)
    
    def _get_pairwise_correlation_analysis(self):
        """
        Lazy loading for pairwise correlation analysis.
        Only computes it once when first needed (for historical scenarios).
        """
        if self._pairwise_corr_analysis is None:
            print("Running pairwise correlation analysis...")
            baseline_summary, stress_summary = run_pairwise_correlation_analysis(self.portfolio_dict)
            self._pairwise_corr_analysis = {
                'baseline_summary': baseline_summary,
                'stress_summary': stress_summary
            }
            print("Pairwise correlation analysis completed.")
        return self._pairwise_corr_analysis
    
    def _filter_betas_for_scenario(self, etf_shocks: dict):
        """
        Filter cached betas to only include ETFs relevant to current scenario.
        """
        filtered_betas = {}
        for ticker in self.tickers:
            filtered_betas[ticker] = {
                etf: self.cached_betas[ticker].get(etf, 0.0)
                for etf in etf_shocks.keys()
            }
        return filtered_betas
    
    def run_workflow(self):
        """
        Run stress test workflow for all scenarios using cached betas.
        Pairwise correlation analysis is included only for historical scenarios.
        
        Returns:
        - dict: Results for all scenarios
        """
        all_results = {}
        
        # Process historical scenarios
        for scenario_name, scenario_data in historical_scenarios.items():
            # Extract ETF shocks (exclude date fields)
            etf_shocks = {k: v for k, v in scenario_data.items() 
                          if k not in ['start_date', 'end_date']}
            
            # Filter betas for this scenario's ETFs
            scenario_betas = self._filter_betas_for_scenario(etf_shocks)
            
            # Run stress test engine with cached betas
            engine_results = run_stress_test_engine(
                self.portfolio_dict, 
                etf_shocks,
                pre_calculated_betas=scenario_betas
            )
            
            # Convert to format expected by analysis functions
            scenario_results = self._format_engine_results(
                engine_results, 
                scenario_name, 
                etf_shocks
            )
            
            # Run analysis functions (including pairwise correlation for historical scenarios)
            analysis_results = {
                'scenario_name': scenario_name,
                'scenario_type': 'historical',
                'etf_shocks': etf_shocks,
                'stock_returns': engine_results['expected_returns'],
                'industry_returns': industry_returns_analysis(scenario_results, self.portfolio_dict),
                'contribution': contribution_analysis(scenario_results, self.portfolio_dict),
                'performance': performance_analysis(scenario_results, self.portfolio_dict),
                'pairwise_correlation_analysis': self._get_pairwise_correlation_analysis()
            }
            
            all_results[f'historical_{scenario_name}'] = analysis_results
        
        # Process hypothetical scenarios
        for scenario_name, etf_shocks in hypothetical_scenarios.items():
            # Filter betas for this scenario's ETFs
            scenario_betas = self._filter_betas_for_scenario(etf_shocks)
            
            # Run stress test engine with cached betas
            engine_results = run_stress_test_engine(
                self.portfolio_dict,
                etf_shocks,
                pre_calculated_betas=scenario_betas
            )
            
            # Convert to format expected by analysis functions
            scenario_results = self._format_engine_results(
                engine_results, 
                scenario_name, 
                etf_shocks
            )
            
            # Run analysis functions
            analysis_results = {
                'scenario_name': scenario_name,
                'scenario_type': 'hypothetical',
                'etf_shocks': etf_shocks,
                'stock_returns': engine_results['expected_returns'],
                'industry_returns': industry_returns_analysis(scenario_results, self.portfolio_dict),
                'contribution': contribution_analysis(scenario_results, self.portfolio_dict),
                'performance': performance_analysis(scenario_results, self.portfolio_dict)
            }
            
            all_results[f'hypothetical_{scenario_name}'] = analysis_results
        
        return all_results
    
    def _format_engine_results(self, engine_results, scenario_name, etf_shocks):
        """
        Helper function to format engine results for analysis functions.
        
        Parameters:
        - engine_results: Results from run_stress_test_engine
        - scenario_name: Name of the scenario
        - etf_shocks: ETF shock values
        
        Returns:
        - dict: Formatted results for analysis functions
        """
        position_details_list = []
        
        for ticker, return_pct in engine_results['expected_returns'].items():
            position = self.portfolio_dict[ticker]["position"]
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

def run_stress_test_workflow(portfolio_dict: dict):
    """
    Legacy function for backward compatibility.
    Creates a StressTestRunner instance and runs the workflow.
    
    Parameters:
    - portfolio_dict: Dictionary with tickers as keys and 'conviction'/'position' as values
    
    Returns:
    - dict: Results for all scenarios
    """
    runner = StressTestRunner(portfolio_dict)
    return runner.run_workflow()

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
    
    # Create runner instance (fetches data once)
    print("Creating StressTestRunner instance...")
    runner = StressTestRunner(portfolio_dict)
    
    # Run the workflow using cached betas
    print("Running stress test workflow with cached betas...")
    results = runner.run_workflow()
    
    print(json.dumps(results, indent=4))
    print(get_token_count(results))