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
    "  - [0.10, 0.30] -> between 0.10 and 0.30\n"
    "  - [null, 0.30] -> anything up to 0.30 (no minimum)\n"
    "  - [0.10, null] -> anything above 0.10 (no maximum)\n\n"
    "**CLASSIFICATION FILTERS:** Use arrays to select from multiple categories (OR logic):\n"
    "  - industries: ['equity_etfs'] -> only equity ETFs\n"
    "  - sub_industries: ['dividend_strategies', 'quality'] -> dividend OR quality strategy ETFs\n\n"
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
    "  - Classification: industries, sub_industries\n"
    "  - Cost: expense_ratio, nav\n"
    "  - Performance: ann_ret, ann_vol, information_ratio\n"
    "  - Risk: beta, alpha\n"
    "  - Income: dividend_yield_ttm\n"
    "  - Size: market_cap, dollar_volume\n"
    "  - QUANT (daily-frequency metrics for algo strategy universe selection):\n"
    "      * Volatility: atr_pct, bb_width, vol_regime_pctile, yang_zhang_vol, vol_ratio_short_long\n"
    "      * Momentum quality: momentum_12m_1m_skip, risk_adj_momentum, rsi_14d, tsmom\n"
    "      * Mean-reversion: hurst_exponent (<0.5=reverting, >0.5=trending), autocorrelation_1d\n"
    "      * Trend strength: adx_14d (<20 no trend, >25 trending)\n"
    "      * Risk/Performance: max_drawdown_1y, sharpe_ratio (rf-adjusted, distinct from information_ratio), sortino_ratio, cvar_95\n"
    "      * Distribution: return_skewness, return_kurtosis, positive_return_ratio\n"
    "      * Return quality: equity_curve_r2\n\n"
    "**NOTES:**\n"
    "  - All ETFs must have price >= $5 (penny ETFs excluded)\n"
    "  - All parameters are optional - use only the filters you need\n"
    "  - IMPORTANT: All percentage values are decimals (divided by 100):\n"
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
            "Average daily dollar trading volume (price x volume)."
        ),
        # ============================================================
        # QUANT SCREENER — 20 daily-frequency metrics for algo-strategy
        # universe selection.
        # ============================================================
        # Quant - Volatility
        "atr_pct": _range_param("ATR(14) / close. Normalized volatility comparable across price levels."),
        "bb_width": _range_param("Bollinger Bandwidth (20, 2 stds). Low = squeeze, high = expansion."),
        "vol_regime_pctile": _range_param("Percentile rank (0-1) of current 20d vol within 252d history."),
        "yang_zhang_vol": _range_param("Yang-Zhang 20d annualized vol (OHLC estimator, handles gaps)."),
        "vol_ratio_short_long": _range_param("20d vol / 60d vol. >1 = expanding, <1 = compressing."),
        # Quant - Momentum quality
        "momentum_12m_1m_skip": _range_param("Academic 12-1 momentum: 12-month return skipping last 21d."),
        "risk_adj_momentum": _range_param("AQR-style risk-adjusted momentum."),
        "rsi_14d": _range_param("RSI(14) last value (0-100)."),
        "tsmom": _range_param("Time-series momentum signal."),
        # Quant - Mean-reversion
        "hurst_exponent": _range_param("Hurst on log-returns. <0.5=reverting, >0.5=trending."),
        "autocorrelation_1d": _range_param("Lag-1 autocorrelation of daily returns over 252d."),
        # Quant - Trend
        "adx_14d": _range_param("ADX(14). <20 no trend, 25-40 established, >40 strong."),
        # Quant - Risk & performance
        "max_drawdown_1y": _range_param("Max drawdown over trailing 252d (decimal, negative)."),
        "sharpe_ratio": _range_param("Rf-adjusted Sharpe. Distinct from information_ratio (no rf)."),
        "sortino_ratio": _range_param("Downside-risk-adjusted return."),
        "cvar_95": _range_param("Mean of worst 5% daily returns (decimal, negative). Tail risk."),
        # Quant - Distribution
        "return_skewness": _range_param("Skewness of daily returns (252d)."),
        "return_kurtosis": _range_param("Excess kurtosis of daily returns (252d)."),
        "positive_return_ratio": _range_param("% of days with positive returns (0-1)."),
        # Quant - Return quality
        "equity_curve_r2": _range_param("R^2 of cumulative returns vs time (252d). Smooth curve signal."),
    },
    "additionalProperties": False,
}
