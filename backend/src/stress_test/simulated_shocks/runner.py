import pandas as pd
from backend.src.stress_test.simulated_shocks.engine import multi_factor_market_shock
from backend.src.stress_test.simulated_shocks.scenarios import (
    stagflation_scenario,
    energy_supply_shock,
    credit_crunch_banking_stress,
    fed_overtightening,
    sticky_inflation,
    credit_stress
)
from backend.src.stress_test.simulated_shocks.analysis import (
    industry_returns_analysis,
    contribution_analysis,
    performance_analysis
)
from backend.src.utils.token_count import get_token_count

class CustomScenarioStressTest:
    def __init__(self, portfolio_dict, period_days=730):
        portfolio_data = [{'ticker': t, 'position': d['position'], 'allocation': d['conviction']} for t, d in portfolio_dict.items()]
        self.portfolio = pd.DataFrame(portfolio_data)
        self.period_days = period_days
        self.scenarios = {
            'stagflation_scenario': stagflation_scenario,
            'energy_supply_shock': energy_supply_shock,
            'credit_crunch_banking_stress': credit_crunch_banking_stress,
            'fed_overtightening': fed_overtightening,
            'sticky_inflation': sticky_inflation,
            'credit_stress': credit_stress,
        }

    
    def run_all_scenarios(self):
        dict = {}

        for scenario in self.scenarios:
            results = multi_factor_market_shock(portfolio_df=self.portfolio, shocks=self.scenarios[scenario], scenario_name=scenario)

            contrib_analysis = contribution_analysis(results)
            perf_analysis = performance_analysis(results)
            industry_returns = industry_returns_analysis(results)

            dict[scenario] = {
                'scenario_name': results['scenario_name'],
                'scenario_shocks': {k: f"{round(v * 100, 1)}%" for k, v in results['scenario_etf_moves'].items()},
                'portfolio_pnl': f"{round(float(results['total_portfolio_pnl']) * 100, 2)}%",
                'spy_pnl': f"{round(float(results['spy_pnl']) * 100, 2)}%",
                'contribution_analysis': contrib_analysis,
                'performance_analysis': perf_analysis,
                'industry_returns': industry_returns
        }

        return dict
    

if __name__ == "__main__":
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

    test = CustomScenarioStressTest(portfolio_dict)
    results = test.run_all_scenarios()

    print(get_token_count(results))
    print(results)


