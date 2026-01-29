# Enum Constants for Classification Filters
VALID_INDUSTRIES = [
    "fixed_income_etfs",
    "equity_etfs",
    "commodity_etfs",
    "cryptocurrency_etfs",
    "alternative_etfs",
]

VALID_SUB_INDUSTRIES = [
    "global_regions_dividends",
    "world",
    "equity_long_short_tactical",
    "industrial_metals",
    "crypto",
    "asset_allocation",
    "commodity_basket",
    "environmental_social_and_corporate_governance",
    "single_country_small_and_mid_caps",
    "dividend_strategies",
    "precious_metals",
    "sectors",
    "artificial_intelligence",
    "collateralized_loan_obligation",
    "industrial_commodities",
    "strategies",
    "regional_banks",
    "interest_rate_and_inflation_hedge",
    "fundamental",
    "hedge_fund_replication",
    "commodities",
    "quality",
    "broad_bond_index_etfs",
    "multi",
    "us_major_index",
    "fundamentally_weighted",
    "global_dividends",
    "energy",
    "factors",
    "u_s_municipal_bond_etfs",
    "global_equities",
    "senior_loans",
    "corporate_bond_etfs",
    "base_metals",
    "abs_and_mbs",
    "treasuries",
    "securitized_products",
    "preferred_stock",
    "volatility",
    "us_factors",
    "u_s_sector_reits",
    "developed_countries",
    "risk_parity",
    "global_real_estate",
    "credit",
    "managed_futures",
    "regions",
    "business_development_company",
    "convertible_bonds",
    "agricultural_commodities",
    "sovereign",
    "equal_weighted",
    "defense",
    "emerging_markets",
]

# Tool Schema Constants
ETF_SCREENER_DESCRIPTION = (
    "Screen ETFs based on performance, risk, cost, and classification criteria. "
    "Returns matching ETFs with their key metrics.\n\n"
    "**RANGE FORMAT:** All numeric filters use [min, max] arrays:\n"
    "  • [0.10, 0.30] → between 0.10 and 0.30\n"
    "  • [null, 0.30] → anything up to 0.30 (no minimum)\n"
    "  • [0.10, null] → anything above 0.10 (no maximum)\n\n"
    "**CLASSIFICATION FILTERS:** Use arrays to select from multiple categories (OR logic):\n"
    "  • industries: ['equity_etfs'] → only equity ETFs\n"
    "  • sub_industries: ['dividend_strategies', 'quality'] → dividend OR quality strategy ETFs\n\n"
    "**EXAMPLES:**\n"
    "  # Low-cost equity ETFs with strong performance:\n"
    "  {\"industries\": [\"equity_etfs\"], \"expense_ratio\": [null, 0.002], \"ann_ret\": [0.10, null]}\n\n"
    "  # Low volatility fixed income ETFs:\n"
    "  {\"industries\": [\"fixed_income_etfs\"], \"ann_vol\": [null, 0.10]}\n\n"
    "  # High dividend yield ETFs:\n"
    "  {\"sub_industries\": [\"dividend_strategies\", \"global_dividends\"], "
    "\"dividend_yield_ttm\": [0.03, null]}\n\n"
    "  # Low beta commodity ETFs:\n"
    "  {\"industries\": [\"commodity_etfs\"], \"beta\": [null, 0.5]}\n\n"
    "  # Large-cap ETFs with positive alpha:\n"
    "  {\"market_cap\": [1000000000, null], \"alpha\": [0, null]}\n\n"
    "  # US major index ETFs with high information ratio:\n"
    "  {\"sub_industries\": [\"us_major_index\"], \"information_ratio\": [0.5, null]}\n\n"
    "**PARAMETER CATEGORIES:**\n"
    "  • Classification: industries, sub_industries\n"
    "  • Cost: expense_ratio, nav\n"
    "  • Performance: ann_ret, ann_vol, information_ratio\n"
    "  • Risk: beta, alpha\n"
    "  • Income: dividend_yield_ttm\n"
    "  • Size: market_cap, dollar_volume\n\n"
    "**NOTES:**\n"
    "  • All ETFs must have price >= $5 (penny ETFs excluded)\n"
    "  • All parameters are optional - use only the filters you need\n"
    "  • IMPORTANT: All percentage values are decimals (divided by 100):\n"
    "    - expense_ratio: 0.002 = 0.20% expense ratio\n"
    "    - ann_ret: 0.15 = 15% annual return\n"
    "    - ann_vol: 0.20 = 20% volatility\n"
    "    - dividend_yield_ttm: 0.03 = 3% yield\n"
    "    - alpha: 0.02 = 2% alpha"
)


# Helper to create range parameter schema
def _range_param(description: str) -> dict:
    """Create a range parameter schema [min, max] where null means unbounded."""
    return {
        "type": "array",
        "description": f"{description} Format: [min, max]. Use null for unbounded.",
        "items": {"type": ["number", "null"]},
        "minItems": 2,
        "maxItems": 2,
    }


ETF_SCREENER_PARAMETERS = {
    "type": "object",
    "properties": {
        # Classification Filters
        "industries": {
            "type": "array",
            "description": (
                "Filter by ETF industry(ies). Multiple values use OR logic. "
                "Example: ['equity_etfs', 'fixed_income_etfs']"
            ),
            "items": {"type": "string", "enum": VALID_INDUSTRIES},
        },
        "sub_industries": {
            "type": "array",
            "description": (
                "Filter by ETF sub-industry(ies). Multiple values use OR logic. "
                "Example: ['dividend_strategies', 'us_major_index', 'treasuries']"
            ),
            "items": {"type": "string", "enum": VALID_SUB_INDUSTRIES},
        },
        # Cost Metrics
        "expense_ratio": _range_param(
            "Expense ratio (decimal, e.g., 0.002 = 0.20%)."
        ),
        "nav": _range_param("Net Asset Value per share in USD."),
        # Performance Metrics
        "ann_ret": _range_param(
            "Annualized return (decimal, e.g., 0.15 = 15%)."
        ),
        "ann_vol": _range_param(
            "Annualized volatility (decimal, e.g., 0.20 = 20%)."
        ),
        "information_ratio": _range_param(
            "Information ratio (annualized return / annualized volatility)."
        ),
        # Risk Metrics
        "beta": _range_param("Beta relative to market benchmark."),
        "alpha": _range_param(
            "Alpha relative to market benchmark (decimal, e.g., 0.02 = 2%)."
        ),
        # Income Metrics
        "dividend_yield_ttm": _range_param(
            "TTM dividend yield (decimal, e.g., 0.03 = 3%)."
        ),
        # Size Metrics
        "market_cap": _range_param("Market capitalization (AUM) in USD."),
        "dollar_volume": _range_param(
            "Average daily dollar trading volume (price × volume)."
        ),
    },
    "additionalProperties": False,
}
