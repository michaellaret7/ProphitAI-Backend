from typing import Optional, Sequence
import numpy as np
from backend.src.data_models.style_factors_models import QualityFactorMetrics
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository

class QualityFactors:
    def __init__(self, ticker: str):
        self.ticker = ticker

        self.fundamental_repository = FundamentalDataRepository()
        self.cash_flow_statement = self.fundamental_repository.fetch_cash_flow_statement(self.ticker)
        self.balance_sheet = self.fundamental_repository.fetch_balance_sheet(self.ticker)
        self.income_statement = self.fundamental_repository.fetch_income_statement(self.ticker)
        self.financial_metrics = self.fundamental_repository.fetch_financial_metrics(self.ticker)
        self.estimates = self.fundamental_repository.fetch_fundamental_estimates(self.ticker)

        # Basic financial statement items
        self.net_income = self.income_statement[0]['net_income']
        self.revenue = self.income_statement[0]['revenue']
        self.gross_profit = self.income_statement[0]['gross_profit']
        self.ebit = self.income_statement[0]['ebit']
        self.ebitda = self.income_statement[0]['operating_income'] + self.cash_flow_statement[0]['depreciation_and_amortization'] if self.income_statement[0]['operating_income'] is not None and self.cash_flow_statement[0]['depreciation_and_amortization'] is not None else None
        self.free_cash_flow = self.cash_flow_statement[0]['free_cash_flow']
        self.operating_cash_flow = self.cash_flow_statement[0]['net_cash_flow_from_operations']
        self.dividends = self.cash_flow_statement[0]['dividends_and_other_cash_distributions']
        # Note: dividends can be negative, representing share buybacks
        
        # Balance sheet items
        self.total_assets = self.balance_sheet[0]['total_assets']
        self.avg_total_assets = self.balance_sheet[0]['total_assets']  # Using current as avg not available
        self.total_equity = self.balance_sheet[0]['shareholders_equity']
        self.avg_total_equity = self.balance_sheet[0]['shareholders_equity']  # Using current as avg not available
        self.total_debt = self.balance_sheet[0]['total_debt']
        self.current_assets = self.balance_sheet[0]['current_assets']
        self.current_liabilities = self.balance_sheet[0]['current_liabilities']
        self.inventory = self.balance_sheet[0]['inventory']
        self.cash_and_equivalents = self.balance_sheet[0]['cash_and_equivalents']
        self.working_capital = self.balance_sheet[0]['current_assets'] - self.balance_sheet[0]['current_liabilities'] if self.balance_sheet[0]['current_assets'] is not None and self.balance_sheet[0]['current_liabilities'] is not None else None
        self.retained_earnings = self.balance_sheet[0]['retained_earnings']
        self.total_liabilities = self.balance_sheet[0]['total_liabilities']
        self.eps = self.financial_metrics[0]['earnings_per_share']
        
        # Market data
        self.market_value_equity = float(self.financial_metrics[0]['market_cap'])
        self.sales = self.income_statement[0]['revenue']  # Same as revenue
        
        # Specialized inputs
        self.nopat = self.income_statement[0]['ebit'] * (1 - 0.21) if self.income_statement[0]['ebit'] is not None else None  # EBIT * (1 - tax rate)
        self.invested_capital = self.balance_sheet[0]['shareholders_equity'] + self.balance_sheet[0]['total_debt'] - self.balance_sheet[0]['cash_and_equivalents'] if self.balance_sheet[0]['shareholders_equity'] is not None and self.balance_sheet[0]['total_debt'] is not None and self.balance_sheet[0]['cash_and_equivalents'] is not None else None
        self.interest_expense = self.income_statement[0]['interest_expense']
        
        # Time series data (not available in current dataset)
        self.eps_quarterly_8 = [self.financial_metrics[i]['earnings_per_share'] for i in range(min(8, len(self.financial_metrics)))] if len(self.financial_metrics) >= 1 else []
        
        # Analyst estimates (not available in current dataset)
        self.eps_estimate_now = self.estimates[1]['eps'] if len(self.estimates) > 1 else None
        self.eps_estimate_3m_ago = self.estimates[0]['eps'] if len(self.estimates) > 0 else None

    def return_on_equity(self) -> Optional[float]:
        """
        ROE = net_income ÷ average_total_equity
        """
        if self.avg_total_equity is None or self.net_income is None or self.avg_total_equity <= 0:
            return None
        return self.net_income / self.avg_total_equity

    def return_on_assets(self) -> Optional[float]:
        """
        ROA = net_income ÷ average_total_assets
        """
        if self.avg_total_assets is None or self.net_income is None or self.avg_total_assets <= 0:
            return None
        return self.net_income / self.avg_total_assets

    def roic(self) -> Optional[float]:
        """
        ROIC = NOPAT ÷ invested_capital
        """
        if self.invested_capital is None or self.nopat is None or self.invested_capital <= 0:
            return None
        return self.nopat / self.invested_capital

    def gross_profitability(self) -> Optional[float]:
        """
        Novy-Marx Gross Profitability = gross_profit ÷ total_assets
        """
        if self.total_assets is None or self.gross_profit is None or self.total_assets <= 0:
            return None
        return self.gross_profit / self.total_assets

    def gross_margin(self) -> Optional[float]:
        """
        Gross Margin = gross_profit ÷ revenue
        
        Note: This is different from gross_profitability which divides by assets
        """
        if self.revenue is None or self.gross_profit is None or self.revenue == 0:
            return None
        return self.gross_profit / self.revenue

    def net_margin(self) -> Optional[float]:
        """
        Net Margin = net_income ÷ revenue
        """
        if self.revenue is None or self.net_income is None or self.revenue == 0:
            return None
        return self.net_income / self.revenue

    def fcf_margin(self) -> Optional[float]:
        """
        FCF Margin = free_cash_flow ÷ revenue
        """
        if self.revenue is None or self.free_cash_flow is None or self.revenue == 0:
            return None
        return self.free_cash_flow / self.revenue

    def debt_to_equity(self) -> Optional[float]:
        """
        Debt/Equity = total_debt ÷ total_equity
        """
        if self.total_equity is None or self.total_debt is None or self.total_equity == 0:
            return None
        return self.total_debt / self.total_equity

    def net_debt_to_ebitda(self) -> Optional[float]:
        """
        Net Debt / EBITDA

        net_debt = total_debt − cash_and_equivalents
        """
        if self.ebitda is None or self.total_debt is None or self.cash_and_equivalents is None or self.ebitda <= 0:
            return None
        net_debt = self.total_debt - self.cash_and_equivalents
        return net_debt / self.ebitda

    def interest_coverage(self) -> Optional[float]:
        """
        Interest Coverage = EBIT ÷ interest_expense
        
        Note: Returns None when interest_expense is 0 or negative.
        Companies with zero interest expense have no debt service requirements,
        which is typically a sign of strong financial health.
        """
        if self.ebit is None or self.interest_expense is None or self.interest_expense <= 0:
            return None  # No meaningful ratio when no interest expense
        return self.ebit / self.interest_expense

    def quick_ratio(self) -> Optional[float]:
        """
        Quick Ratio = (current_assets − inventory) ÷ current_liabilities
        """
        if self.current_liabilities == 0 or self.current_assets is None or self.inventory is None or self.current_liabilities is None:
            return None
        return (self.current_assets - self.inventory) / self.current_liabilities

    def altman_z_score(self) -> Optional[float]:
        """
        Altman Z-Score (original 1968 five-ratio model).

        Z = 1.2·(WC/TA) + 1.4·(RE/TA) + 3.3·(EBIT/TA)
            + 0.6·(MVE/TL) + 1.0·(Sales/TA)
        """
        if (self.total_assets is None or self.total_liabilities is None or 
            self.total_assets == 0 or self.total_liabilities == 0 or 
            self.working_capital is None or self.retained_earnings is None or 
            self.ebit is None or self.sales is None):
            return None
        wc_ta = self.working_capital / self.total_assets
        re_ta = self.retained_earnings / self.total_assets
        ebit_ta = self.ebit / self.total_assets
        mve_tl = self.market_value_equity / self.total_liabilities
        sales_ta = self.sales / self.total_assets
        z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mve_tl + 1.0 * sales_ta
        return z

    def accruals_ratio(self) -> Optional[float]:
        """
        Accruals = (net_income − CFO) ÷ total_assets

        Higher (more positive) accruals → lower quality earnings.
        """
        if self.total_assets is None or self.net_income is None or self.operating_cash_flow is None or self.total_assets == 0:
            return None
        return (self.net_income - self.operating_cash_flow) / self.total_assets

    def earnings_stability(self) -> Optional[float]:
        """
        Earnings Stability = std_dev(EPS for last 8 quarters)
                            ÷ mean(EPS for last 8 quarters)
        
        This is the coefficient of variation (CV) of earnings.
        Interpretation:
        - < 0.15 (15%): Very stable earnings
        - 0.15-0.30 (15-30%): Moderate stability
        - 0.30-0.50 (30-50%): High variability
        - > 0.50 (50%): Very unstable earnings
        
        Lower values indicate more consistent earnings (higher quality).
        """
        if len(self.eps_quarterly_8) < 6:
            return None
        
        eps_arr = np.array(self.eps_quarterly_8, dtype=float)
        mean_eps = eps_arr.mean()
        if mean_eps == 0:
            return None
        return eps_arr.std(ddof=0) / mean_eps

    def eps_revision_3m(self) -> Optional[float]:
        """
        EPS Revision 3m = (EPS_now - EPS_3m_ago) ÷ EPS_3m_ago
        """
        if self.eps_estimate_3m_ago == 0 or self.eps_estimate_now is None or self.eps_estimate_3m_ago is None:
            return None
        return (self.eps_estimate_now - self.eps_estimate_3m_ago) / self.eps_estimate_3m_ago

    def dividend_payout(self) -> Optional[float]:
        """
        Dividend Payout = dividends ÷ net_income
        
        Note: Negative values typically indicate share buybacks rather than dividends.
        A negative payout ratio means the company is returning cash to shareholders
        through repurchases instead of dividends.
        """
        if self.net_income is None or self.dividends is None or self.net_income == 0:
            return None
        return self.dividends / self.net_income

    def asset_turnover(self) -> Optional[float]:
        """
        Asset Turnover = revenue / total_assets
        """
        if self.total_assets is None or self.revenue is None or self.total_assets == 0:
            return None
        return self.revenue / self.total_assets

    def cash_conversion_ratio(self) -> Optional[float]:
        """
        Cash Conversion Ratio = operating_cash_flow / net_income
        """
        if self.net_income is None or self.operating_cash_flow is None or self.net_income == 0:
            return None
        return self.operating_cash_flow / self.net_income

    def cash_flow_to_debt_ratio(self) -> Optional[float]:
        """
        Cash Flow to Debt Ratio = operating_cash_flow / total_debt
        """
        if self.total_debt is None or self.operating_cash_flow is None or self.total_debt == 0:
            return None
        return self.operating_cash_flow / self.total_debt
        
    def conservative_financing(self) -> Optional[bool]:
        """
        Conservative Financing = total_debt < total_assets
        """
        if self.total_debt is None or self.total_assets is None:
            return None
        return self.total_debt < self.total_assets

    def return_on_capital_employed(self) -> Optional[float]:
        """
        Return on Capital Employed = ebit / (total_assets - current_liabilities)
        """
        if self.total_assets is None or self.current_liabilities is None or self.ebit is None:
            return None
        capital_employed = self.total_assets - self.current_liabilities
        if capital_employed is None or capital_employed == 0:
            return None
        return self.ebit / capital_employed

    def calc_all(self) -> QualityFactorMetrics:
        """
        Calculate all quality factor metrics at once.
        
        Parameters
        ----------
        All parameters are optional. Pass None or omit parameters for metrics you cannot calculate.
        
        Returns
        -------
        QualityMetrics
            Pydantic model containing all calculated quality metrics
        """

        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None"""
            return round(value, decimals) if value is not None else None

        return QualityFactorMetrics(
            return_on_equity=safe_round(self.return_on_equity()),
            return_on_assets=safe_round(self.return_on_assets()),
            roic=safe_round(self.roic()),
            gross_profitability=safe_round(self.gross_profitability()),
            gross_margin=safe_round(self.gross_margin()),
            net_margin=safe_round(self.net_margin()),
            fcf_margin=safe_round(self.fcf_margin()),
            debt_to_equity=safe_round(self.debt_to_equity()),
            net_debt_to_ebitda=safe_round(self.net_debt_to_ebitda()),
            interest_coverage=safe_round(self.interest_coverage()),
            quick_ratio=safe_round(self.quick_ratio()),
            altman_z_score=safe_round(self.altman_z_score()),
            accruals_ratio=safe_round(self.accruals_ratio()),
            earnings_stability=safe_round(self.earnings_stability()),
            eps_revision_3m=safe_round(self.eps_revision_3m()),
            dividend_payout=safe_round(self.dividend_payout()),
            asset_turnover=safe_round(self.asset_turnover()),
            cash_conversion_ratio=safe_round(self.cash_conversion_ratio()),
            cash_flow_to_debt_ratio=safe_round(self.cash_flow_to_debt_ratio()),
            conservative_financing=self.conservative_financing(),
            return_on_capital_employed=safe_round(self.return_on_capital_employed())
        )


if __name__ == "__main__":
    from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository

    quality_factors = QualityFactors('AAPL')
    print(quality_factors.calc_all())