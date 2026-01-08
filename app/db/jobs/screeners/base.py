"""
Screener Base Utilities

Common utilities and constants used by ETF and Equity screener updaters.
"""
import numpy as np


# FMP API key -> EquityScreener column name mapping
RATIO_KEY_MAP = {
    'dividendYielTTM': 'dividend_yield_ttm',
    'peRatioTTM': 'pe_ratio_ttm',
    'pegRatioTTM': 'peg_ratio_ttm',
    'priceToBookRatioTTM': 'price_to_book_ratio_ttm',
    'priceToSalesRatioTTM': 'price_to_sales_ratio_ttm',
    'priceToFreeCashFlowsRatioTTM': 'price_to_free_cash_flows_ratio_ttm',
    'priceToOperatingCashFlowsRatioTTM': 'price_to_operating_cash_flows_ratio_ttm',
    'enterpriseValueMultipleTTM': 'enterprise_value_multiple_ttm',
    'payoutRatioTTM': 'payout_ratio_ttm',
    'grossProfitMarginTTM': 'gross_profit_margin_ttm',
    'operatingProfitMarginTTM': 'operating_profit_margin_ttm',
    'pretaxProfitMarginTTM': 'pretax_profit_margin_ttm',
    'netProfitMarginTTM': 'net_profit_margin_ttm',
    'returnOnAssetsTTM': 'return_on_assets_ttm',
    'returnOnEquityTTM': 'return_on_equity_ttm',
    'returnOnCapitalEmployedTTM': 'return_on_capital_employed_ttm',
    'operatingCashFlowSalesRatioTTM': 'operating_cash_flow_sales_ratio_ttm',
    'freeCashFlowOperatingCashFlowRatioTTM': 'free_cash_flow_operating_cash_flow_ratio_ttm',
    'capitalExpenditureCoverageRatioTTM': 'capital_expenditure_coverage_ratio_ttm',
    'dividendPaidAndCapexCoverageRatioTTM': 'dividend_paid_and_capex_coverage_ratio_ttm',
    'debtRatioTTM': 'debt_ratio_ttm',
    'debtEquityRatioTTM': 'debt_equity_ratio_ttm',
    'longTermDebtToCapitalizationTTM': 'long_term_debt_to_capitalization_ttm',
    'totalDebtToCapitalizationTTM': 'total_debt_to_capitalization_ttm',
    'interestCoverageTTM': 'interest_coverage_ttm',
    'cashFlowToDebtRatioTTM': 'cash_flow_to_debt_ratio_ttm',
    'shortTermCoverageRatiosTTM': 'short_term_coverage_ratios_ttm',
    'companyEquityMultiplierTTM': 'company_equity_multiplier_ttm',
    'quickRatioTTM': 'quick_ratio_ttm',
    'cashRatioTTM': 'cash_ratio_ttm',
    'cashConversionCycleTTM': 'cash_conversion_cycle_ttm',
    'receivablesTurnoverTTM': 'receivables_turnover_ttm',
    'payablesTurnoverTTM': 'payables_turnover_ttm',
    'inventoryTurnoverTTM': 'inventory_turnover_ttm',
    'assetTurnoverTTM': 'asset_turnover_ttm',
}


def safe_round(value, decimals: int = 4):
    """
    Safely round a value, returning None for NaN/Inf/non-numeric types.

    Args:
        value: The value to round
        decimals: Number of decimal places

    Returns:
        Rounded float or None if invalid
    """
    if value is None:
        return None
    try:
        if np.isnan(value) or np.isinf(value):
            return None
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def safe_divide(numerator, denominator):
    """
    Safely divide two numbers, returning None for invalid operations.

    Args:
        numerator: The dividend
        denominator: The divisor

    Returns:
        Division result or None if invalid
    """
    if numerator is None or denominator is None:
        return None
    try:
        if denominator == 0 or np.isnan(denominator):
            return None
        result = float(numerator) / float(denominator)
        if np.isnan(result) or np.isinf(result):
            return None
        return result
    except (TypeError, ValueError, ZeroDivisionError):
        return None
