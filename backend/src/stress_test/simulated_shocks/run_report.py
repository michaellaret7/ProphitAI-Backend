import pandas as pd
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker
from backend.src.stress_test.simulated_shocks.custom_market_shock import multi_factor_market_shock, simulated_market_shock
from backend.src.stress_test.simulated_shocks.scenarios import (
    stagflation_scenario,
    energy_supply_shock,
    credit_crunch_banking_stress,
    fed_overtightening,
    sticky_inflation,
    credit_stress
)
import json
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

    def get_industry_distribution(self):
        """Get industry mapping for all tickers in portfolio."""
        session = MarketSession()
        tickers = self.portfolio['ticker'].tolist()
        tickers_db = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
        session.close()
        
        # Create ticker to industry mapping
        industry_map = {ticker.ticker: ticker.industry for ticker in tickers_db}
        return industry_map
    
    def industry_returns_analysis(self, scenario_results):
        """Calculate returns per industry from scenario results."""
        df = scenario_results['position_details'].copy()
        
        # Get industry mapping
        industry_map = self.get_industry_distribution()
        df['industry'] = df['ticker'].map(industry_map)
        
        # Group by industry and calculate total PnL
        industry_returns = df.groupby('industry')['pnl'].sum()
        
        # Convert to percentage and format
        industry_returns_dict = {}
        for industry, pnl in industry_returns.items():
            industry_returns_dict[industry] = f"{round(float(pnl) * 100, 2)}%"
        
        return industry_returns_dict
    
    def contribution_analysis(self, scenario_results):
        """
        Perform contribution analysis on scenario results.
        
        Parameters:
        - scenario_results: Dict returned from multi_factor_market_shock
        
        Returns:
        - dict: Analysis results including position ranking, concentration metrics, and long/short attribution
        """
        df = scenario_results['position_details'].copy()
        
        # 1. Position P&L Impact: Rank all positions by absolute P&L contribution
        df['abs_pnl'] = df['pnl'].abs()
        position_ranking = df.sort_values('abs_pnl', ascending=False)[['ticker', 'position', 'pnl', 'abs_pnl']]
        
        # 2. Concentration Metric: Calculate % of total loss from top positions
        total_abs_loss = float(df['abs_pnl'].sum())
        top_3_loss = float(position_ranking.head(3)['abs_pnl'].sum())
        top_5_loss = float(position_ranking.head(5)['abs_pnl'].sum())
        top_10_loss = float(position_ranking.head(10)['abs_pnl'].sum())
        
        concentration_metrics = {
            'top_3_concentration': f"{round(float((top_3_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%",
            'top_5_concentration': f"{round(float((top_5_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%",
            'top_10_concentration': f"{round(float((top_10_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%"
        }
        
        # 3. Long vs Short Attribution: Sum P&L separately for long book vs short book
        long_pnl = float(df[df['position'] == 'long']['pnl'].sum())
        short_pnl = float(df[df['position'] == 'short']['pnl'].sum())
        total_pnl = float(df['pnl'].sum())
        total_abs_pnl = float(df['abs_pnl'].sum())
        
        # Calculate contribution as % of total absolute P&L for consistent interpretation
        attribution = {
            'long_book_pnl': f"{round(long_pnl * 100, 2)}%",
            'short_book_pnl': f"{round(short_pnl * 100, 2)}%",
            'total_pnl': f"{round(total_pnl * 100, 2)}%",
            'long_contribution_pct': f"{round(float((abs(long_pnl) / total_abs_pnl) * 100), 2)}%" if total_abs_pnl != 0 else "0.0%",
            'short_contribution_pct': f"{round(float((abs(short_pnl) / total_abs_pnl) * 100), 2)}%" if total_abs_pnl != 0 else "0.0%"
        }
        
        return {
            'concentration_metrics': concentration_metrics,
            'long_short_attribution': attribution
        }
    
    def performance_analysis(self, scenario_results):
        """
        Perform performance analysis on scenario results.
        
        Parameters:
        - scenario_results: Dict returned from multi_factor_market_shock
        """
        df = scenario_results['position_details'].copy()

        # --- 1. Top 5 Tickers by Beta Exposure ---
        beta_columns = [col for col in df.columns if col.startswith('beta_')]
        
        # Melt the DataFrame to have one row per ticker-beta combination
        melted_betas = df.melt(id_vars=['ticker'], value_vars=beta_columns, var_name='beta_factor', value_name='beta_value')
        
        # Get the top 5 highest beta values across all factors
        top_5_betas = melted_betas.nlargest(5, 'beta_value')
        top_5_betas['beta_value'] = top_5_betas['beta_value'].round(4)
        
        top_betas = top_5_betas.to_dict('records')


        # --- 2. Top & Bottom 3 Tickers by P&L ---
        top_3_pnl_df = df.nlargest(3, 'pnl')[['ticker', 'pnl']].copy()
        top_3_pnl_df['pnl'] = top_3_pnl_df['pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
        top_3_pnl = top_3_pnl_df.to_dict('records')

        bottom_3_pnl_df = df.nsmallest(3, 'pnl')[['ticker', 'pnl']].copy()
        bottom_3_pnl_df['pnl'] = bottom_3_pnl_df['pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
        bottom_3_pnl = bottom_3_pnl_df.to_dict('records')

        # --- 3. Top & Bottom 3 Tickers by Total Stock Return ---
        top_3_return_df = df.nlargest(3, 'total_stock_return')[['ticker', 'total_stock_return']].copy()
        top_3_return_df['total_stock_return'] = top_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
        top_3_return = top_3_return_df.to_dict('records')

        bottom_3_return_df = df.nsmallest(3, 'total_stock_return')[['ticker', 'total_stock_return']].copy()
        bottom_3_return_df['total_stock_return'] = bottom_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
        bottom_3_return = bottom_3_return_df.to_dict('records')
        
        performance_dict = {
            '5_highest_beta_exposures': top_betas,
            'pnl_analysis': {
                'top_3_performers': top_3_pnl,
                'bottom_3_performers': bottom_3_pnl
            },
            'return_analysis': {
                'top_3_performers': top_3_return,
                'bottom_3_performers': bottom_3_return
            }
        }
        
        return performance_dict
    
    def run_all_scenarios(self):
        dict = {}

        for scenario in self.scenarios:
            results = multi_factor_market_shock(portfolio_df=self.portfolio, shocks=self.scenarios[scenario], scenario_name=scenario)

            contribution_analysis = self.contribution_analysis(results)
            performance_analysis = self.performance_analysis(results)
            industry_returns = self.industry_returns_analysis(results)

            dict[scenario] = {
                'scenario_name': results['scenario_name'],
                'scenario_shocks': {k: f"{round(v * 100, 1)}%" for k, v in results['scenario_etf_moves'].items()},
                'portfolio_pnl': f"{round(float(results['total_portfolio_pnl']) * 100, 2)}%",
                'spy_pnl': f"{round(float(results['spy_pnl']) * 100, 2)}%",
                'contribution_analysis': contribution_analysis,
                'performance_analysis': performance_analysis,
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


