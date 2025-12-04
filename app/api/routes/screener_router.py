from fastapi import APIRouter, Query
from typing import Optional, List
from app.api.controller.screeners import run_equity_screener, run_etf_screener

router = APIRouter(tags=["Screeners 🔍"])

@router.get("/screeners/equity")
def equity_screener(
    # Classification filters (lists)
    sectors: Optional[List[str]] = Query(None),
    industries: Optional[List[str]] = Query(None),
    sub_industries: Optional[List[str]] = Query(None),
    # Ticker table filters (ranges as [min, max])
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    avg_volume_min: Optional[float] = None,
    avg_volume_max: Optional[float] = None,
    eps_min: Optional[float] = None,
    eps_max: Optional[float] = None,
    dollar_volume_min: Optional[float] = None,
    dollar_volume_max: Optional[float] = None,
    # Momentum & Performance metrics
    momentum_1m_min: Optional[float] = None,
    momentum_1m_max: Optional[float] = None,
    momentum_3m_min: Optional[float] = None,
    momentum_3m_max: Optional[float] = None,
    momentum_6m_min: Optional[float] = None,
    momentum_6m_max: Optional[float] = None,
    ann_return_min: Optional[float] = None,
    ann_return_max: Optional[float] = None,
    ann_vol_min: Optional[float] = None,
    ann_vol_max: Optional[float] = None,
    beta_vs_spy_min: Optional[float] = None,
    beta_vs_spy_max: Optional[float] = None,
    beta_vs_sector_min: Optional[float] = None,
    beta_vs_sector_max: Optional[float] = None,
    alpha_vs_spy_min: Optional[float] = None,
    alpha_vs_spy_max: Optional[float] = None,
    alpha_vs_sector_min: Optional[float] = None,
    alpha_vs_sector_max: Optional[float] = None,
    ebit_cagr_5yr_min: Optional[float] = None,
    ebit_cagr_5yr_max: Optional[float] = None,
    ebit_cagr_3yr_min: Optional[float] = None,
    ebit_cagr_3yr_max: Optional[float] = None,
    revenue_cagr_3yr_min: Optional[float] = None,
    revenue_cagr_3yr_max: Optional[float] = None,
    # Valuation ratios
    dividend_yield_ttm_min: Optional[float] = None,
    dividend_yield_ttm_max: Optional[float] = None,
    pe_ratio_ttm_min: Optional[float] = None,
    pe_ratio_ttm_max: Optional[float] = None,
    peg_ratio_ttm_min: Optional[float] = None,
    peg_ratio_ttm_max: Optional[float] = None,
    price_to_book_ratio_ttm_min: Optional[float] = None,
    price_to_book_ratio_ttm_max: Optional[float] = None,
    price_to_sales_ratio_ttm_min: Optional[float] = None,
    price_to_sales_ratio_ttm_max: Optional[float] = None,
    price_to_free_cash_flows_ratio_ttm_min: Optional[float] = None,
    price_to_free_cash_flows_ratio_ttm_max: Optional[float] = None,
    price_to_operating_cash_flows_ratio_ttm_min: Optional[float] = None,
    price_to_operating_cash_flows_ratio_ttm_max: Optional[float] = None,
    enterprise_value_multiple_ttm_min: Optional[float] = None,
    enterprise_value_multiple_ttm_max: Optional[float] = None,
    # Profitability ratios
    payout_ratio_ttm_min: Optional[float] = None,
    payout_ratio_ttm_max: Optional[float] = None,
    gross_profit_margin_ttm_min: Optional[float] = None,
    gross_profit_margin_ttm_max: Optional[float] = None,
    operating_profit_margin_ttm_min: Optional[float] = None,
    operating_profit_margin_ttm_max: Optional[float] = None,
    pretax_profit_margin_ttm_min: Optional[float] = None,
    pretax_profit_margin_ttm_max: Optional[float] = None,
    net_profit_margin_ttm_min: Optional[float] = None,
    net_profit_margin_ttm_max: Optional[float] = None,
    return_on_assets_ttm_min: Optional[float] = None,
    return_on_assets_ttm_max: Optional[float] = None,
    return_on_equity_ttm_min: Optional[float] = None,
    return_on_equity_ttm_max: Optional[float] = None,
    return_on_capital_employed_ttm_min: Optional[float] = None,
    return_on_capital_employed_ttm_max: Optional[float] = None,
    # Cash flow ratios
    operating_cash_flow_sales_ratio_ttm_min: Optional[float] = None,
    operating_cash_flow_sales_ratio_ttm_max: Optional[float] = None,
    free_cash_flow_operating_cash_flow_ratio_ttm_min: Optional[float] = None,
    free_cash_flow_operating_cash_flow_ratio_ttm_max: Optional[float] = None,
    capital_expenditure_coverage_ratio_ttm_min: Optional[float] = None,
    capital_expenditure_coverage_ratio_ttm_max: Optional[float] = None,
    dividend_paid_and_capex_coverage_ratio_ttm_min: Optional[float] = None,
    dividend_paid_and_capex_coverage_ratio_ttm_max: Optional[float] = None,
    # Debt ratios
    debt_ratio_ttm_min: Optional[float] = None,
    debt_ratio_ttm_max: Optional[float] = None,
    debt_equity_ratio_ttm_min: Optional[float] = None,
    debt_equity_ratio_ttm_max: Optional[float] = None,
    long_term_debt_to_capitalization_ttm_min: Optional[float] = None,
    long_term_debt_to_capitalization_ttm_max: Optional[float] = None,
    total_debt_to_capitalization_ttm_min: Optional[float] = None,
    total_debt_to_capitalization_ttm_max: Optional[float] = None,
    interest_coverage_ttm_min: Optional[float] = None,
    interest_coverage_ttm_max: Optional[float] = None,
    cash_flow_to_debt_ratio_ttm_min: Optional[float] = None,
    cash_flow_to_debt_ratio_ttm_max: Optional[float] = None,
    short_term_coverage_ratios_ttm_min: Optional[float] = None,
    short_term_coverage_ratios_ttm_max: Optional[float] = None,
    company_equity_multiplier_ttm_min: Optional[float] = None,
    company_equity_multiplier_ttm_max: Optional[float] = None,
    # Liquidity ratios
    quick_ratio_ttm_min: Optional[float] = None,
    quick_ratio_ttm_max: Optional[float] = None,
    cash_ratio_ttm_min: Optional[float] = None,
    cash_ratio_ttm_max: Optional[float] = None,
    # Efficiency ratios
    cash_conversion_cycle_ttm_min: Optional[float] = None,
    cash_conversion_cycle_ttm_max: Optional[float] = None,
    receivables_turnover_ttm_min: Optional[float] = None,
    receivables_turnover_ttm_max: Optional[float] = None,
    payables_turnover_ttm_min: Optional[float] = None,
    payables_turnover_ttm_max: Optional[float] = None,
    inventory_turnover_ttm_min: Optional[float] = None,
    inventory_turnover_ttm_max: Optional[float] = None,
    asset_turnover_ttm_min: Optional[float] = None,
    asset_turnover_ttm_max: Optional[float] = None,
):
    """
    Screen equities based on various filters.

    All numeric filters accept min/max parameters (e.g., price_min, price_max).
    Classification filters (sectors, industries, sub_industries) accept lists.

    Returns matching stocks with their metrics.
    """
    kwargs = {}

    # Classification filters
    if sectors:
        kwargs["sectors"] = sectors
    if industries:
        kwargs["industries"] = industries
    if sub_industries:
        kwargs["sub_industries"] = sub_industries

    # Helper to build range tuples from min/max params
    range_fields = [
        "price", "market_cap", "avg_volume", "eps", "dollar_volume",
        "momentum_1m", "momentum_3m", "momentum_6m", "ann_return", "ann_vol",
        "beta_vs_spy", "beta_vs_sector", "alpha_vs_spy", "alpha_vs_sector",
        "ebit_cagr_5yr", "ebit_cagr_3yr", "revenue_cagr_3yr",
        "dividend_yield_ttm", "pe_ratio_ttm", "peg_ratio_ttm",
        "price_to_book_ratio_ttm", "price_to_sales_ratio_ttm",
        "price_to_free_cash_flows_ratio_ttm", "price_to_operating_cash_flows_ratio_ttm",
        "enterprise_value_multiple_ttm",
        "payout_ratio_ttm", "gross_profit_margin_ttm", "operating_profit_margin_ttm",
        "pretax_profit_margin_ttm", "net_profit_margin_ttm",
        "return_on_assets_ttm", "return_on_equity_ttm", "return_on_capital_employed_ttm",
        "operating_cash_flow_sales_ratio_ttm", "free_cash_flow_operating_cash_flow_ratio_ttm",
        "capital_expenditure_coverage_ratio_ttm", "dividend_paid_and_capex_coverage_ratio_ttm",
        "debt_ratio_ttm", "debt_equity_ratio_ttm", "long_term_debt_to_capitalization_ttm",
        "total_debt_to_capitalization_ttm", "interest_coverage_ttm",
        "cash_flow_to_debt_ratio_ttm", "short_term_coverage_ratios_ttm",
        "company_equity_multiplier_ttm",
        "quick_ratio_ttm", "cash_ratio_ttm",
        "cash_conversion_cycle_ttm", "receivables_turnover_ttm",
        "payables_turnover_ttm", "inventory_turnover_ttm", "asset_turnover_ttm",
    ]

    local_vars = locals()
    for field in range_fields:
        min_val = local_vars.get(f"{field}_min")
        max_val = local_vars.get(f"{field}_max")
        if min_val is not None or max_val is not None:
            kwargs[field] = [min_val, max_val]

    return run_equity_screener(**kwargs)


@router.get("/screeners/etf")
def etf_screener(
    # Classification filters (lists)
    industries: Optional[List[str]] = Query(None),
    sub_industries: Optional[List[str]] = Query(None),
    # Size metrics (ranges as min/max)
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    dollar_volume_min: Optional[float] = None,
    dollar_volume_max: Optional[float] = None,
    # Cost metrics
    expense_ratio_min: Optional[float] = None,
    expense_ratio_max: Optional[float] = None,
    nav_min: Optional[float] = None,
    nav_max: Optional[float] = None,
    # Performance metrics
    ann_ret_min: Optional[float] = None,
    ann_ret_max: Optional[float] = None,
    ann_vol_min: Optional[float] = None,
    ann_vol_max: Optional[float] = None,
    information_ratio_min: Optional[float] = None,
    information_ratio_max: Optional[float] = None,
    # Risk metrics
    beta_min: Optional[float] = None,
    beta_max: Optional[float] = None,
    alpha_min: Optional[float] = None,
    alpha_max: Optional[float] = None,
    # Income metrics
    dividend_yield_ttm_min: Optional[float] = None,
    dividend_yield_ttm_max: Optional[float] = None,
):
    """
    Screen ETFs based on various filters.

    All numeric filters accept min/max parameters (e.g., expense_ratio_min, expense_ratio_max).
    Classification filters (industries, sub_industries) accept lists.

    Returns matching ETFs with their metrics.
    """
    kwargs = {}

    # Classification filters
    if industries:
        kwargs["industries"] = industries
    if sub_industries:
        kwargs["sub_industries"] = sub_industries

    # Helper to build range tuples from min/max params
    range_fields = [
        "market_cap", "dollar_volume",
        "expense_ratio", "nav",
        "ann_ret", "ann_vol", "information_ratio",
        "beta", "alpha",
        "dividend_yield_ttm",
    ]

    local_vars = locals()
    for field in range_fields:
        min_val = local_vars.get(f"{field}_min")
        max_val = local_vars.get(f"{field}_max")
        if min_val is not None or max_val is not None:
            kwargs[field] = [min_val, max_val]

    return run_etf_screener(**kwargs)
