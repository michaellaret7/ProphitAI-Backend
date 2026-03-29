"""TTM financial ratios tools.

Provides tools for fetching trailing twelve months (TTM) financial
ratios for companies, enabling current-state fundamental analysis.
Supports batched multi-ticker calls.
"""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA


# ================================
# --> Constants
# ================================

# Reason: curated subset — drops 22 duplicate/redundant/niche fields from FMP's 57
CURATED_TTM_FIELDS: set[str] = {
    # Valuation
    "peRatioTTM", "pegRatioTTM", "priceToBookRatioTTM", "priceToSalesRatioTTM",
    "priceToFreeCashFlowsRatioTTM", "priceToOperatingCashFlowsRatioTTM",
    "enterpriseValueMultipleTTM", "payoutRatioTTM",
    # Profitability
    "grossProfitMarginTTM", "operatingProfitMarginTTM",
    "pretaxProfitMarginTTM", "netProfitMarginTTM",
    # Tax
    "effectiveTaxRateTTM",
    # Leverage
    "debtRatioTTM", "longTermDebtToCapitalizationTTM",
    "totalDebtToCapitalizationTTM", "cashFlowToDebtRatioTTM",
    # Liquidity
    "currentRatioTTM", "quickRatioTTM", "cashRatioTTM",
    # Efficiency
    "daysOfSalesOutstandingTTM", "daysOfInventoryOutstandingTTM",
    "operatingCycleTTM", "daysOfPayablesOutstandingTTM",
    "cashConversionCycleTTM", "inventoryTurnoverTTM", "assetTurnoverTTM",
    # Cash Flow
    "operatingCashFlowPerShareTTM", "freeCashFlowPerShareTTM", "cashPerShareTTM",
    "operatingCashFlowSalesRatioTTM", "freeCashFlowOperatingCashFlowRatioTTM",
}


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ratios_ttm", category="fundamentals")
def get_ratios_ttm(
    tickers: list[str],
) -> str:
    """
    Get curated TTM financial ratios for one or more tickers.

    Returns ~31 high-signal ratios per ticker (filtered from FMP's 57 raw fields).
    Drops duplicates, niche metrics, and fields already served by `ticker_factors`
    (ROE, ROA, D/E, interest coverage, dividend yield).

    **Ratio Categories:**
    - Valuation: P/E, PEG, P/B, P/S, P/FCF, P/OCF, EV/EBITDA, payout ratio
    - Profitability: Gross, operating, pretax, net profit margins
    - Tax: Effective tax rate
    - Leverage: Debt ratio, LT debt/cap, total debt/cap, CF-to-debt
    - Liquidity: Current, quick, cash ratios
    - Efficiency: DSO, DIO, DPO, operating & cash conversion cycles, turnover
    - Cash Flow: OCF/share, FCF/share, cash/share, OCF/sales, FCF/OCF

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'KO'])

    Returns:
        Curated TTM financial ratios across valuation, profitability, leverage,
        liquidity, efficiency, and cash flow categories

    Examples:
        get_ratios_ttm(tickers=['AAPL', 'MSFT'])
        >>> {"success": True, "data": {"results": {"AAPL": {...}, "MSFT": {...}}, "errors": {}}}

    Raises:
        Exception: If data retrieval fails
    """
    tickers = [t.upper().strip() for t in tickers]

    results: dict = {}
    errors: dict = {}

    try:
        fmp = FMP_API_DATA()
    except Exception as e:
        return error_response(f"Failed to initialize FMP API: {str(e)}")

    for t in tickers:
        try:
            data = fmp.get_ratios_ttm(t)

            if data is None or len(data) == 0:
                errors[t] = f"No TTM ratios found for {t}"
                continue

            if isinstance(data, list) and len(data) > 0:
                ratios = {
                    k: round(v, 4) if isinstance(v, (int, float)) else v
                    for k, v in data[0].items()
                    if k in CURATED_TTM_FIELDS
                }
                results[t] = ratios
        except Exception as e:
            errors[t] = f"Failed to retrieve TTM ratios for {t}: {str(e)}"

    return success_response({"results": results, "errors": errors})


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_ratios_ttm.tool)
