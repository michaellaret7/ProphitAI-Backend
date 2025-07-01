from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
import numpy as np
from scipy import stats
from typing import List, Dict
from backend.src.data_models.style_factors_models import GrowthFactorMetrics

class GrowthFactors:
    def __init__(self, ticker: str):
        self.ticker = ticker

        self.fundamental_repository = FundamentalDataRepository()
        self.cash_flow_statement = self.fundamental_repository.fetch_cash_flow_statement(self.ticker)
        self.balance_sheet = self.fundamental_repository.fetch_balance_sheet(self.ticker)
        self.income_statement = self.fundamental_repository.fetch_income_statement(self.ticker)
        self.financial_metrics = self.fundamental_repository.fetch_financial_metrics(self.ticker)
        self.estimates = self.fundamental_repository.fetch_fundamental_estimates(self.ticker)
        
        self.current_eps = self.financial_metrics[0]['earnings_per_share']
        self.previous_eps = self.financial_metrics[1]['earnings_per_share']
        self.beginning_eps = self.financial_metrics[len(self.financial_metrics) - 1]['earnings_per_share']
        self.years = len(self.financial_metrics)/4
        
        # Extract revenue data
        self.current_revenue = self.income_statement[0]['revenue']
        self.previous_revenue = self.income_statement[1]['revenue'] if len(self.income_statement) > 1 else 0
        
        # Extract all revenue values for sales trend analysis
        self.revenue_data = [period['revenue'] for period in self.income_statement if period['revenue'] is not None]
        
        # Extract free cash flow data
        self.current_fcf = self.cash_flow_statement[0]['free_cash_flow']
        self.previous_fcf = self.cash_flow_statement[1]['free_cash_flow'] if len(self.cash_flow_statement) > 1 else 0
        
        # Extract PE ratio
        self.pe_ratio = self.financial_metrics[0]['price_to_earnings_ratio']
        
        # Extract ROE data
        self.current_roe = self.financial_metrics[0]['return_on_equity']
        self.previous_roe = self.financial_metrics[1]['return_on_equity'] if len(self.financial_metrics) > 1 else 0
        
        # Extract ROIC data
        self.current_roic = self.financial_metrics[0]['return_on_invested_capital']
        self.previous_roic = self.financial_metrics[1]['return_on_invested_capital'] if len(self.financial_metrics) > 1 else 0
        
        # Extract book value per share data
        self.current_bvps = self.financial_metrics[0]['book_value_per_share']
        self.previous_bvps = self.financial_metrics[1]['book_value_per_share'] if len(self.financial_metrics) > 1 else 0
        
        # Extract operating cash flow data
        self.current_ocf = self.cash_flow_statement[0]['net_cash_flow_from_operations']
        self.previous_ocf = self.cash_flow_statement[1]['net_cash_flow_from_operations'] if len(self.cash_flow_statement) > 1 else 0

        
    def eps_growth_rate(self) -> float:
        """
        Calculate Earnings Per Share (EPS) Growth Rate
        
        Args:
            current_eps: Current period EPS
            previous_eps: Previous period EPS
        
        Returns:
            EPS growth rate as percentage
        """
        if self.previous_eps == 0 or self.current_eps is None or self.previous_eps is None:
            return np.nan if self.current_eps == 0 else np.inf
        return ((self.current_eps - self.previous_eps) / abs(self.previous_eps)) * 100
    
    def eps_cagr(self) -> float:
        """
        Calculate EPS Compound Annual Growth Rate (CAGR)
        
        Args:
            ending_eps: EPS at end of period
            beginning_eps: EPS at beginning of period
            years: Number of years in the period
        
        Returns:
            EPS CAGR as decimal (multiply by 100 for percentage)
        """

        if self.current_eps is None or self.beginning_eps is None or self.beginning_eps <= 0 or self.current_eps <= 0 or self.years <= 0:
            return np.nan
        return (self.current_eps / self.beginning_eps) ** (1 / self.years) - 1
    
    def revenue_growth_rate(self) -> float:
        """
        Calculate Revenue Growth Rate
        
        Returns:
            Revenue growth rate as percentage
        """
        if self.previous_revenue == 0 or self.current_revenue is None or self.previous_revenue is None:
            return np.nan if self.current_revenue == 0 else np.inf
        return ((self.current_revenue - self.previous_revenue) / abs(self.previous_revenue)) * 100

    def sales_trend_growth_factor(self) -> float:
        """
        Calculate Bloomberg's Sales Trend Growth Factor using linear regression
        
        Returns:
            Sales trend growth factor
        """
        if len(self.revenue_data) < 2:
            return np.nan
        
        # Filter out None values
        valid_revenue_data = [rev for rev in self.revenue_data if rev is not None]
        
        if len(valid_revenue_data) < 2:
            return np.nan
        
        # Calculate slope using scipy's linregress for more statistical robustness
        x = np.arange(len(valid_revenue_data))
        slope, _, _, _, _ = stats.linregress(x, valid_revenue_data)
        
        # Calculate average of absolute sales values
        avg_abs_sales = np.mean(np.abs(valid_revenue_data))
        
        if avg_abs_sales == 0:
            return np.nan
        
        return slope / avg_abs_sales
    
    def fcf_growth_rate(self) -> float:
        """
        Calculate Free Cash Flow Growth Rate
        
        Returns:
            FCF growth rate as percentage
        """
        if self.previous_fcf == 0 or self.current_fcf is None or self.previous_fcf is None:
            return np.nan if self.current_fcf == 0 else np.inf
        return ((self.current_fcf - self.previous_fcf) / abs(self.previous_fcf)) * 100

    def peg_ratio(self) -> float:
        """
        Calculate Price-to-Earnings-Growth (PEG) Ratio
        
        Returns:
            PEG ratio
        """
        if self.pe_ratio is None:
            return np.nan
        
        eps_growth = self.eps_growth_rate()
        if eps_growth == 0 or np.isnan(eps_growth):
            return np.nan
        return self.pe_ratio / eps_growth

    def roe_growth_rate(self) -> float:
        """
        Calculate Return on Equity (ROE) Growth Rate
        
        Returns:
            ROE growth rate as percentage
        """
        if self.previous_roe == 0 or self.current_roe is None or self.previous_roe is None:
            return np.nan if self.current_roe == 0 else np.inf
        return ((self.current_roe - self.previous_roe) / abs(self.previous_roe)) * 100

    def roic_growth_rate(self) -> float:
        """
        Calculate Return on Invested Capital (ROIC) Growth Rate
        
        Returns:
            ROIC growth rate as percentage
        """
        if self.previous_roic == 0 or self.current_roic is None or self.previous_roic is None:
            return np.nan if self.current_roic == 0 else np.inf
        return ((self.current_roic - self.previous_roic) / abs(self.previous_roic)) * 100
    
    def book_value_growth_rate(self) -> float:
        """
        Calculate Book Value Per Share Growth Rate
        
        Returns:
            Book value growth rate as percentage
        """
        if self.previous_bvps == 0 or self.current_bvps is None or self.previous_bvps is None:
            return np.nan if self.current_bvps == 0 else np.inf
        return ((self.current_bvps - self.previous_bvps) / abs(self.previous_bvps)) * 100

    def ocf_growth_rate(self) -> float:
        """
        Calculate Operating Cash Flow Growth Rate
        
        Returns:
            OCF growth rate as percentage
        """
        if self.previous_ocf == 0 or self.current_ocf is None or self.previous_ocf is None:
            return np.nan if self.current_ocf == 0 else np.inf
        return ((self.current_ocf - self.previous_ocf) / abs(self.previous_ocf)) * 100
    

    
    def calc_all(self) -> GrowthFactorMetrics:
        """
        Calculate all growth factor metrics at once.
        
        Returns
        -------
        GrowthFactorMetrics
            Pydantic model containing all calculated growth metrics
        """
        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None or NaN"""
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return None
            return round(value, decimals)

        return GrowthFactorMetrics(
            eps_growth_rate=safe_round(self.eps_growth_rate()),
            eps_cagr=safe_round(self.eps_cagr()),
            revenue_growth_rate=safe_round(self.revenue_growth_rate()),
            sales_trend_growth_factor=safe_round(self.sales_trend_growth_factor()),
            fcf_growth_rate=safe_round(self.fcf_growth_rate()),
            peg_ratio=safe_round(self.peg_ratio()),
            roe_growth_rate=safe_round(self.roe_growth_rate()),
            roic_growth_rate=safe_round(self.roic_growth_rate()),
            book_value_growth_rate=safe_round(self.book_value_growth_rate()),
            ocf_growth_rate=safe_round(self.ocf_growth_rate())
        )
    
if __name__ == "__main__":
    growth_factors = GrowthFactors(ticker='AAPL')
    print(growth_factors.calc_all())