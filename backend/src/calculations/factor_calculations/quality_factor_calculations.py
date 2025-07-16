from typing import Optional, Sequence
import numpy as np
from backend.src.data_models.style_factors_models import QualityFactorMetrics
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import *
from sqlalchemy import desc

class QualityFactors:
    def __init__(self, ticker: str):
        self.ticker = ticker

        market_session = MarketSession()
        self.cash_flow_statement = market_session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(CashFlowStatement.date)).all()
        self.balance_sheet = market_session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(BalanceSheet.date)).all()
        self.income_statement = market_session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(IncomeStatement.date)).all()
        self.financial_metrics = market_session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(FinancialRatio.date)).all()
        self.estimates = market_session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(AnalystEstimate.date)).all()
        
        # Get ticker info for market cap
        self.ticker_info = market_session.query(Ticker).filter(Ticker.ticker == self.ticker).first()
        market_session.close()

        # Simple null-safe data access - Basic financial statement items
        self.net_income = float(self.income_statement[0].netIncome) if self.income_statement and self.income_statement[0].netIncome else None
        self.revenue = float(self.income_statement[0].revenue) if self.income_statement and self.income_statement[0].revenue else None
        self.gross_profit = float(self.income_statement[0].grossProfit) if self.income_statement and self.income_statement[0].grossProfit else None
        
        # Calculate EBIT from operating income
        self.ebit = float(self.income_statement[0].operatingIncome) if self.income_statement and self.income_statement[0].operatingIncome else None
        
        # EBITDA is already available in income statement
        self.ebitda = float(self.income_statement[0].ebitda) if self.income_statement and self.income_statement[0].ebitda else None
            
        self.free_cash_flow = float(self.cash_flow_statement[0].freeCashFlow) if self.cash_flow_statement and self.cash_flow_statement[0].freeCashFlow else None
        self.operating_cash_flow = float(self.cash_flow_statement[0].netCashProvidedByOperatingActivities) if self.cash_flow_statement and self.cash_flow_statement[0].netCashProvidedByOperatingActivities else None
        self.dividends = float(self.cash_flow_statement[0].dividendsPaid) if self.cash_flow_statement and self.cash_flow_statement[0].dividendsPaid else None
        # Note: dividends can be negative, representing share buybacks
        
        # Balance sheet items
        self.total_assets = float(self.balance_sheet[0].totalAssets) if self.balance_sheet and self.balance_sheet[0].totalAssets else None
        self.avg_total_assets = self.total_assets  # Using current as avg not available
        self.total_equity = float(self.balance_sheet[0].totalStockholdersEquity) if self.balance_sheet and self.balance_sheet[0].totalStockholdersEquity else None
        self.avg_total_equity = self.total_equity  # Using current as avg not available
        self.total_debt = float(self.balance_sheet[0].totalDebt) if self.balance_sheet and self.balance_sheet[0].totalDebt else None
        self.current_assets = float(self.balance_sheet[0].totalCurrentAssets) if self.balance_sheet and self.balance_sheet[0].totalCurrentAssets else None
        self.current_liabilities = float(self.balance_sheet[0].totalCurrentLiabilities) if self.balance_sheet and self.balance_sheet[0].totalCurrentLiabilities else None
        self.inventory = float(self.balance_sheet[0].inventory) if self.balance_sheet and self.balance_sheet[0].inventory else None
        self.cash_and_equivalents = float(self.balance_sheet[0].cashAndCashEquivalents) if self.balance_sheet and self.balance_sheet[0].cashAndCashEquivalents else None
        
        # Calculate working capital
        self.working_capital = (self.current_assets - self.current_liabilities) if self.current_assets is not None and self.current_liabilities is not None else None
            
        self.retained_earnings = float(self.balance_sheet[0].retainedEarnings) if self.balance_sheet and self.balance_sheet[0].retainedEarnings else None
        self.total_liabilities = float(self.balance_sheet[0].totalLiabilities) if self.balance_sheet and self.balance_sheet[0].totalLiabilities else None
        self.eps = float(self.income_statement[0].eps) if self.income_statement and self.income_statement[0].eps else None
        
        # Market data
        self.market_value_equity = float(self.ticker_info.market_cap) if self.ticker_info and self.ticker_info.market_cap else None
        self.sales = self.revenue  # Same as revenue
        
        # Specialized inputs
        self.nopat = (self.ebit * (1 - 0.21)) if self.ebit is not None else None  # EBIT * (1 - tax rate)
        
        # Calculate invested capital
        self.invested_capital = (self.total_equity + self.total_debt - self.cash_and_equivalents) if self.total_equity is not None and self.total_debt is not None and self.cash_and_equivalents is not None else None
            
        self.interest_expense = float(self.income_statement[0].interestExpense) if self.income_statement and self.income_statement[0].interestExpense else None
        
        # Time series data - get last 8 quarters of EPS
        self.eps_quarterly_8 = [float(stmt.eps) for stmt in self.income_statement[:8] if stmt.eps is not None] if self.income_statement else []
        
        # Analyst estimates
        self.eps_estimate_now = float(self.estimates[0].epsAvg) if self.estimates and self.estimates[0].epsAvg else None
        self.eps_estimate_3m_ago = float(self.estimates[1].epsAvg) if len(self.estimates) > 1 and self.estimates[1].epsAvg else None

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
        if self.current_assets is None or self.inventory is None or self.current_liabilities is None or self.current_liabilities == 0:
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
        if len(self.eps_quarterly_8) < 4:  # Reduced from 6 to 4 for minimum data points
            return None
        
        eps_arr = np.array(self.eps_quarterly_8, dtype=float)
        mean_eps = eps_arr.mean()

        if mean_eps == 0 or np.isnan(mean_eps):
            return None

        return eps_arr.std(ddof=0) / abs(mean_eps)  # Use absolute value to handle negative mean

    def eps_revision_3m(self) -> Optional[float]:
        """
        EPS Revision 3m = (EPS_now - EPS_3m_ago) ÷ EPS_3m_ago
        """
        if self.eps_estimate_now is None or self.eps_estimate_3m_ago is None or self.eps_estimate_3m_ago == 0:
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
    quality_factors = QualityFactors('AAPL')
    print(quality_factors.calc_all())