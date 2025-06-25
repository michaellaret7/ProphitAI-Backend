from typing import Optional, Sequence
import numpy as np
from backend.src.data_models.style_factors_models import QualityFactorMetrics

class QualityFactors:
    @staticmethod
    def return_on_equity(net_income: float, avg_total_equity: float) -> Optional[float]:
        """
        ROE = net_income ÷ average_total_equity
        """
        if avg_total_equity <= 0:
            return None
        return net_income / avg_total_equity

    @staticmethod
    def return_on_assets(net_income: float, avg_total_assets: float) -> Optional[float]:
        """
        ROA = net_income ÷ average_total_assets
        """
        if avg_total_assets <= 0:
            return None
        return net_income / avg_total_assets

    @staticmethod
    def roic(nopat: float, invested_capital: float) -> Optional[float]:
        """
        ROIC = NOPAT ÷ invested_capital
        """
        if invested_capital <= 0:
            return None
        return nopat / invested_capital

    @staticmethod
    def gross_profitability(gross_profit: float, total_assets: float) -> Optional[float]:
        """
        Novy-Marx Gross Profitability = gross_profit ÷ total_assets
        """
        if total_assets <= 0:
            return None
        return gross_profit / total_assets

    @staticmethod
    def net_margin(net_income: float, revenue: float) -> Optional[float]:
        """
        Net Margin = net_income ÷ revenue
        """
        if revenue == 0:
            return None
        return net_income / revenue

    @staticmethod
    def fcf_margin(free_cash_flow: float, revenue: float) -> Optional[float]:
        """
        FCF Margin = free_cash_flow ÷ revenue
        """
        if revenue == 0:
            return None
        return free_cash_flow / revenue

    @staticmethod
    def debt_to_equity(total_debt: float, total_equity: float) -> Optional[float]:
        """
        Debt/Equity = total_debt ÷ total_equity
        """
        if total_equity == 0:
            return None
        return total_debt / total_equity

    @staticmethod
    def net_debt_to_ebitda(total_debt: float, cash_and_equivalents: float, ebitda: float) -> Optional[float]:
        """
        Net Debt / EBITDA

        net_debt = total_debt − cash_and_equivalents
        """
        if ebitda <= 0:
            return None
        net_debt = total_debt - cash_and_equivalents
        return net_debt / ebitda

    @staticmethod
    def interest_coverage(ebit: float, interest_expense: float) -> Optional[float]:
        """
        Interest Coverage = EBIT ÷ interest_expense
        """
        if interest_expense == 0:
            return None
        return ebit / interest_expense

    @staticmethod
    def quick_ratio(current_assets: float, inventory: float, current_liabilities: float) -> Optional[float]:
        """
        Quick Ratio = (current_assets − inventory) ÷ current_liabilities
        """
        if current_liabilities == 0:
            return None
        return (current_assets - inventory) / current_liabilities

    @staticmethod
    def altman_z_score(working_capital: float, retained_earnings: float, ebit: float, market_value_equity: float, total_liabilities: float, sales: float, total_assets: float) -> Optional[float]:
        """
        Altman Z-Score (original 1968 five-ratio model).

        Z = 1.2·(WC/TA) + 1.4·(RE/TA) + 3.3·(EBIT/TA)
            + 0.6·(MVE/TL) + 1.0·(Sales/TA)
        """
        if total_assets == 0 or total_liabilities == 0:
            return None
        wc_ta = working_capital / total_assets
        re_ta = retained_earnings / total_assets
        ebit_ta = ebit / total_assets
        mve_tl = market_value_equity / total_liabilities
        sales_ta = sales / total_assets
        z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mve_tl + 1.0 * sales_ta
        return z

    @staticmethod
    def accruals_ratio(net_income: float, operating_cash_flow: float, total_assets: float) -> Optional[float]:
        """
        Accruals = (net_income − CFO) ÷ total_assets

        Higher (more positive) accruals → lower quality earnings.
        """
        if total_assets == 0:
            return None
        return (net_income - operating_cash_flow) / total_assets

    @staticmethod
    def earnings_stability(eps_quarterly_8: Sequence[float]) -> Optional[float]:
        """
        Earnings Stability = std_dev(EPS for last 8 quarters)
                            ÷ mean(EPS for last 8 quarters)
        """
        if len(eps_quarterly_8) < 8:
            return None
        eps_arr = np.array(eps_quarterly_8, dtype=float)
        mean_eps = eps_arr.mean()
        if mean_eps == 0:
            return None
        return eps_arr.std(ddof=0) / mean_eps

    @staticmethod
    def piotroski_f_score(nine_test_booleans: Sequence[bool]) -> Optional[int]:
        """
        Piotroski (2000) F-Score: sum of 9 binary signals.

        Pass in a sequence of 9 booleans, each representing:
          1. Positive ROA
          2. Positive ΔROA
          3. Positive CFO
          4. CFO > Net Income
          5. Lower Leverage (ΔLong-term debt < 0)
          6. Higher Current Ratio
          7. No New Shares Issued
          8. Higher Gross Margin
          9. Higher Asset Turnover

        Returns
        -------
        int | None
            0-9 score.  None if length != 9.
        """
        if len(nine_test_booleans) != 9:
            return None
        return int(sum(bool(x) for x in nine_test_booleans))

    @staticmethod
    def eps_revision_3m(eps_estimate_now: float, eps_estimate_3m_ago: float) -> Optional[float]:
        """
        EPS Revision 3m = (EPS_now − EPS_3m_ago) ÷ EPS_3m_ago
        """
        if eps_estimate_3m_ago == 0:
            return None
        return (eps_estimate_now - eps_estimate_3m_ago) / eps_estimate_3m_ago

    @staticmethod
    def dividend_payout(dividends: float, net_income: float) -> Optional[float]:
        """
        Dividend Payout = dividends ÷ net_income
        """
        if net_income == 0:
            return None
        return dividends / net_income

    @staticmethod
    def calc_all(
        # Basic financial statement items
        net_income: Optional[float] = None,
        revenue: Optional[float] = None,
        gross_profit: Optional[float] = None,
        ebit: Optional[float] = None,
        ebitda: Optional[float] = None,
        free_cash_flow: Optional[float] = None,
        operating_cash_flow: Optional[float] = None,
        dividends: Optional[float] = None,
        
        # Balance sheet items
        total_assets: Optional[float] = None,
        avg_total_assets: Optional[float] = None,
        total_equity: Optional[float] = None,
        avg_total_equity: Optional[float] = None,
        total_debt: Optional[float] = None,
        current_assets: Optional[float] = None,
        current_liabilities: Optional[float] = None,
        inventory: Optional[float] = None,
        cash_and_equivalents: Optional[float] = None,
        working_capital: Optional[float] = None,
        retained_earnings: Optional[float] = None,
        total_liabilities: Optional[float] = None,
        
        # Market data
        market_value_equity: Optional[float] = None,
        sales: Optional[float] = None,
        
        # Specialized inputs
        nopat: Optional[float] = None,
        invested_capital: Optional[float] = None,
        interest_expense: Optional[float] = None,
        
        # Time series data
        eps_quarterly_8: Optional[Sequence[float]] = None,
        nine_test_booleans: Optional[Sequence[bool]] = None,
        
        # Analyst estimates
        eps_estimate_now: Optional[float] = None,
        eps_estimate_3m_ago: Optional[float] = None,
    ) -> QualityFactorMetrics:
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
        
        return QualityFactorMetrics(
            return_on_equity=QualityFactors.return_on_equity(net_income, avg_total_equity) if net_income is not None and avg_total_equity is not None else None,
            return_on_assets=QualityFactors.return_on_assets(net_income, avg_total_assets) if net_income is not None and avg_total_assets is not None else None,
            roic=QualityFactors.roic(nopat, invested_capital) if nopat is not None and invested_capital is not None else None,
            gross_profitability=QualityFactors.gross_profitability(gross_profit, total_assets) if gross_profit is not None and total_assets is not None else None,
            net_margin=QualityFactors.net_margin(net_income, revenue) if net_income is not None and revenue is not None else None,
            fcf_margin=QualityFactors.fcf_margin(free_cash_flow, revenue) if free_cash_flow is not None and revenue is not None else None,
            debt_to_equity=QualityFactors.debt_to_equity(total_debt, total_equity) if total_debt is not None and total_equity is not None else None,
            net_debt_to_ebitda=QualityFactors.net_debt_to_ebitda(total_debt, cash_and_equivalents, ebitda) if total_debt is not None and cash_and_equivalents is not None and ebitda is not None else None,
            interest_coverage=QualityFactors.interest_coverage(ebit, interest_expense) if ebit is not None and interest_expense is not None else None,
            quick_ratio=QualityFactors.quick_ratio(current_assets, inventory, current_liabilities) if current_assets is not None and inventory is not None and current_liabilities is not None else None,
            altman_z_score=QualityFactors.altman_z_score(working_capital, retained_earnings, ebit, market_value_equity, total_liabilities, sales, total_assets) if all(x is not None for x in [working_capital, retained_earnings, ebit, market_value_equity, total_liabilities, sales, total_assets]) else None,
            accruals_ratio=QualityFactors.accruals_ratio(net_income, operating_cash_flow, total_assets) if net_income is not None and operating_cash_flow is not None and total_assets is not None else None,
            earnings_stability=QualityFactors.earnings_stability(eps_quarterly_8) if eps_quarterly_8 is not None else None,
            piotroski_f_score=QualityFactors.piotroski_f_score(nine_test_booleans) if nine_test_booleans is not None else None,
            eps_revision_3m=QualityFactors.eps_revision_3m(eps_estimate_now, eps_estimate_3m_ago) if eps_estimate_now is not None and eps_estimate_3m_ago is not None else None,
            dividend_payout=QualityFactors.dividend_payout(dividends, net_income) if dividends is not None and net_income is not None else None,
        )

if __name__ == "__main__":
    import random
    import numpy as np
    
    # Set seed for reproducible results
    np.random.seed(42)
    random.seed(42)
    
    net_income = 850.0  # $850M net income
    revenue = 5200.0    # $5.2B revenue  
    gross_profit = 3100.0  # ~60% gross margin
    ebit = 1050.0       # EBIT
    ebitda = 1250.0     # EBITDA (includes depreciation)
    free_cash_flow = 920.0  # Strong FCF generation
    operating_cash_flow = 1100.0  # Operating cash flow
    dividends = 340.0   # $340M in dividends
    
    # Balance sheet items  
    total_assets = 8500.0
    avg_total_assets = 8200.0  # Average of current and prior year
    total_equity = 4800.0
    avg_total_equity = 4600.0  # Average equity
    total_debt = 2100.0
    current_assets = 3200.0
    current_liabilities = 1800.0
    inventory = 450.0
    cash_and_equivalents = 1200.0
    working_capital = current_assets - current_liabilities  # $1.4B
    retained_earnings = 2800.0
    total_liabilities = total_assets - total_equity  # $3.7B
    
    # Market data
    shares_outstanding = 200.0  # 200M shares
    stock_price = 145.0  # $145 per share
    market_value_equity = shares_outstanding * stock_price  # $29B market cap
    sales = revenue  # Same as revenue
    
    # Specialized inputs
    tax_rate = 0.21  # 21% corporate tax rate
    nopat = ebit * (1 - tax_rate)  # Net Operating Profit After Tax
    invested_capital = total_equity + total_debt - cash_and_equivalents  # ~$5.7B
    interest_expense = 85.0  # $85M interest expense
    
    # Time series data - 8 quarters of EPS
    base_eps = net_income / shares_outstanding  # ~$4.25 EPS
    eps_quarterly_8 = [
        base_eps * random.uniform(0.85, 1.15) for _ in range(8)
    ]  # Some variability around base EPS
    
    # Piotroski F-Score components (9 binary tests)
    nine_test_booleans = [
        True,   # 1. Positive ROA
        True,   # 2. Positive ΔROA  
        True,   # 3. Positive CFO
        True,   # 4. CFO > Net Income
        False,  # 5. Lower Leverage (debt increased)
        True,   # 6. Higher Current Ratio
        False,  # 7. No New Shares Issued (some dilution)
        True,   # 8. Higher Gross Margin
        True,   # 9. Higher Asset Turnover
    ]  # Score should be 7/9
    
    # Analyst estimates
    eps_estimate_now = 4.80  # Current FY estimate
    eps_estimate_3m_ago = 4.65  # 3 months ago estimate (revised up)
    
    print("Testing QualityFactors with comprehensive financial data...")
    print("=" * 60)
    
    # Calculate all quality metrics
    all_metrics = QualityFactors.calc_all(
        # Basic financial statement items
        net_income=net_income,
        revenue=revenue,
        gross_profit=gross_profit,
        ebit=ebit,
        ebitda=ebitda,
        free_cash_flow=free_cash_flow,
        operating_cash_flow=operating_cash_flow,
        dividends=dividends,
        
        # Balance sheet items
        total_assets=total_assets,
        avg_total_assets=avg_total_assets,
        total_equity=total_equity,
        avg_total_equity=avg_total_equity,
        total_debt=total_debt,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        inventory=inventory,
        cash_and_equivalents=cash_and_equivalents,
        working_capital=working_capital,
        retained_earnings=retained_earnings,
        total_liabilities=total_liabilities,
        
        # Market data
        market_value_equity=market_value_equity,
        sales=sales,
        
        # Specialized inputs
        nopat=nopat,
        invested_capital=invested_capital,
        interest_expense=interest_expense,
        
        # Time series data
        eps_quarterly_8=eps_quarterly_8,
        nine_test_booleans=nine_test_booleans,
        
        # Analyst estimates
        eps_estimate_now=eps_estimate_now,
        eps_estimate_3m_ago=eps_estimate_3m_ago,
    )
    
    print("Quality Factor Metrics Results:")
    print("-" * 40)
    for field_name, value in all_metrics.model_dump().items():
        if value is not None:
            if isinstance(value, float):
                print(f"{field_name.replace('_', ' ').title()}: {value:.4f}")
            else:
                print(f"{field_name.replace('_', ' ').title()}: {value}")
        else:
            print(f"{field_name.replace('_', ' ').title()}: N/A")
    
    print("\n" + "=" * 60)
    print("Key Insights from the metrics:")
    print(f"• ROE: {all_metrics.return_on_equity:.2%} - Strong return on equity")
    print(f"• ROA: {all_metrics.return_on_assets:.2%} - Solid asset utilization") 
    print(f"• ROIC: {all_metrics.roic:.2%} - Good returns on invested capital")
    print(f"• Debt/Equity: {all_metrics.debt_to_equity:.2f}x - Moderate leverage")
    print(f"• Interest Coverage: {all_metrics.interest_coverage:.1f}x - Strong debt servicing ability")
    print(f"• Piotroski F-Score: {all_metrics.piotroski_f_score}/9 - High quality score")
    print(f"• Altman Z-Score: {all_metrics.altman_z_score:.2f} - {'Safe' if all_metrics.altman_z_score > 2.99 else 'Caution' if all_metrics.altman_z_score > 1.81 else 'Distress'} zone")