from __future__ import annotations

import yaml
from typing import Any, Dict, List, Optional, Union, Set, Tuple

import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import aliased

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import (
    Ticker,
    FinancialRatio,
    ETFInfo,
    Rating,
    AnalystRecommendation,
    PriceTargetSummary,
)
from app.utils.gpt_parser import parse_with_gpt


class ScreenerConstraints(BaseModel):
    """Pydantic model for stock screener constraints parsed from natural language."""

    # Valuation filters
    market_cap_min: Optional[float] = Field(None, description="Minimum market cap in dollars")
    market_cap_max: Optional[float] = Field(None, description="Maximum market cap in dollars")
    avg_volume_min: Optional[float] = Field(None, description="Minimum average volume")
    avg_volume_max: Optional[float] = Field(None, description="Maximum average volume")
    pe_ratio_min: Optional[float] = Field(None, description="Minimum P/E ratio")
    pe_ratio_max: Optional[float] = Field(None, description="Maximum P/E ratio")
    pb_ratio_min: Optional[float] = Field(None, description="Minimum price-to-book ratio")
    pb_ratio_max: Optional[float] = Field(None, description="Maximum price-to-book ratio")
    ps_ratio_min: Optional[float] = Field(None, description="Minimum price-to-sales ratio")
    ps_ratio_max: Optional[float] = Field(None, description="Maximum price-to-sales ratio")
    price_to_cash_flow_min: Optional[float] = Field(None, description="Minimum price-to-cash-flow ratio")
    price_to_cash_flow_max: Optional[float] = Field(None, description="Maximum price-to-cash-flow ratio")
    price_to_fcf_min: Optional[float] = Field(None, description="Minimum price-to-free-cash-flow ratio")
    price_to_fcf_max: Optional[float] = Field(None, description="Maximum price-to-free-cash-flow ratio")
    price_to_ocf_min: Optional[float] = Field(None, description="Minimum price-to-operating-cash-flow ratio")
    price_to_ocf_max: Optional[float] = Field(None, description="Maximum price-to-operating-cash-flow ratio")
    peg_ratio_min: Optional[float] = Field(None, description="Minimum PEG ratio")
    peg_ratio_max: Optional[float] = Field(None, description="Maximum PEG ratio")
    enterprise_value_multiple_min: Optional[float] = Field(None, description="Minimum EV/EBITDA")
    enterprise_value_multiple_max: Optional[float] = Field(None, description="Maximum EV/EBITDA")
    price_fair_value_min: Optional[float] = Field(None, description="Minimum price/fair value")
    price_fair_value_max: Optional[float] = Field(None, description="Maximum price/fair value")
    dividend_yield_min: Optional[float] = Field(None, description="Minimum dividend yield (decimal)")
    dividend_yield_max: Optional[float] = Field(None, description="Maximum dividend yield (decimal)")

    # Profitability filters
    roe_min: Optional[float] = Field(None, description="Minimum return on equity (decimal)")
    roe_max: Optional[float] = Field(None, description="Maximum return on equity (decimal)")
    roa_min: Optional[float] = Field(None, description="Minimum return on assets (decimal)")
    roa_max: Optional[float] = Field(None, description="Maximum return on assets (decimal)")
    roic_min: Optional[float] = Field(None, description="Minimum return on invested capital (decimal)")
    roic_max: Optional[float] = Field(None, description="Maximum return on invested capital (decimal)")
    gross_margin_min: Optional[float] = Field(None, description="Minimum gross margin (decimal)")
    gross_margin_max: Optional[float] = Field(None, description="Maximum gross margin (decimal)")
    operating_margin_min: Optional[float] = Field(None, description="Minimum operating margin (decimal)")
    operating_margin_max: Optional[float] = Field(None, description="Maximum operating margin (decimal)")
    net_margin_min: Optional[float] = Field(None, description="Minimum net margin (decimal)")
    net_margin_max: Optional[float] = Field(None, description="Maximum net margin (decimal)")

    # Financial health filters
    debt_to_equity_min: Optional[float] = Field(None, description="Minimum debt-to-equity ratio")
    debt_to_equity_max: Optional[float] = Field(None, description="Maximum debt-to-equity ratio")
    current_ratio_min: Optional[float] = Field(None, description="Minimum current ratio")
    current_ratio_max: Optional[float] = Field(None, description="Maximum current ratio")
    quick_ratio_min: Optional[float] = Field(None, description="Minimum quick ratio")
    quick_ratio_max: Optional[float] = Field(None, description="Maximum quick ratio")
    interest_coverage_min: Optional[float] = Field(None, description="Minimum interest coverage ratio")
    interest_coverage_max: Optional[float] = Field(None, description="Maximum interest coverage ratio")

    # Efficiency filters
    asset_turnover_min: Optional[float] = Field(None, description="Minimum asset turnover ratio")
    asset_turnover_max: Optional[float] = Field(None, description="Maximum asset turnover ratio")
    inventory_turnover_min: Optional[float] = Field(None, description="Minimum inventory turnover ratio")
    inventory_turnover_max: Optional[float] = Field(None, description="Maximum inventory turnover ratio")

    # ETF-specific filters
    expense_ratio_min: Optional[float] = Field(None, description="Minimum expense ratio (for ETFs)")
    expense_ratio_max: Optional[float] = Field(None, description="Maximum expense ratio (for ETFs)")
    assets_under_management_min: Optional[float] = Field(None, description="Minimum AUM (for ETFs)")
    assets_under_management_max: Optional[float] = Field(None, description="Maximum AUM (for ETFs)")
    holdings_count_min: Optional[float] = Field(None, description="Minimum number of holdings (for ETFs)")
    holdings_count_max: Optional[float] = Field(None, description="Maximum number of holdings (for ETFs)")

    # Rating filters
    overall_score_min: Optional[float] = Field(None, description="Minimum overall rating score")
    overall_score_max: Optional[float] = Field(None, description="Maximum overall rating score")
    analyst_rating_score_min: Optional[float] = Field(None, description="Minimum analyst rating score")
    analyst_rating_score_max: Optional[float] = Field(None, description="Maximum analyst rating score")

    # Price target filters
    price_target_last_month_min: Optional[float] = Field(None, description="Minimum analyst price target (last month)")
    price_target_last_month_max: Optional[float] = Field(None, description="Maximum analyst price target (last month)")
    price_target_last_quarter_min: Optional[float] = Field(None, description="Minimum analyst price target (last quarter)")
    price_target_last_quarter_max: Optional[float] = Field(None, description="Maximum analyst price target (last quarter)")
    price_target_last_year_min: Optional[float] = Field(None, description="Minimum analyst price target (last year)")
    price_target_last_year_max: Optional[float] = Field(None, description="Maximum analyst price target (last year)")

    # Classification filters
    sector: Optional[Union[str, List[str]]] = Field(None, description="Sector or list of sectors to INCLUDE")
    industry: Optional[Union[str, List[str]]] = Field(None, description="Industry or list of industries to INCLUDE")
    sub_industry: Optional[Union[str, List[str]]] = Field(None, description="Sub-industry or list of sub-industries to INCLUDE")
    sector_exclude: Optional[Union[str, List[str]]] = Field(None, description="Sector or list of sectors to EXCLUDE")
    industry_exclude: Optional[Union[str, List[str]]] = Field(None, description="Industry or list of industries to EXCLUDE")
    sub_industry_exclude: Optional[Union[str, List[str]]] = Field(None, description="Sub-industry or list of sub-industries to EXCLUDE")

    # Company profile filters
    beta_min: Optional[float] = Field(None, description="Minimum beta")
    beta_max: Optional[float] = Field(None, description="Maximum beta")
    is_actively_trading: Optional[bool] = Field(None, description="Filter for actively trading stocks")
    is_adr: Optional[bool] = Field(None, description="Filter for ADRs (American Depositary Receipts)")
    is_fund: Optional[bool] = Field(None, description="Filter for funds")
    shares_outstanding_min: Optional[float] = Field(None, description="Minimum shares outstanding")
    shares_outstanding_max: Optional[float] = Field(None, description="Maximum shares outstanding")

    # Display options
    limit: int = Field(100, description="Maximum results to return")
    offset: int = Field(0, description="Results to skip")
    sort_by: Optional[List[str]] = Field(None, description="Fields to sort by (prefix with '-' for desc)")
    columns: Optional[List[str]] = Field(None, description="Specific columns to return")

class StockScreener:
    """
    High-level stock screener with tuple-based operators and dynamic JOINs.

    - No caching – every call executes a fresh DB query
    - Exposes all available fundamental datapoints present in schemas
    - Joins only the tables needed by active filters, sorts, or selected columns
    """

    def __init__(self) -> None:
        self._synonyms: Dict[str, Tuple[Any, str]] = {}
        self._populate_synonyms()

    def screen(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[List[str]] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> pd.DataFrame:
        """
        Execute a screen with tuple-based filters and dynamic JOINs.

        Args:
            limit: Max rows returned
            offset: Rows to skip
            sort_by: e.g. ["-market_cap", "pe_ratio"] ("-" = DESC)
            columns: Optional explicit output columns across available schemas
            **filters: Tuple/list/str/bool/numeric filter values

        Returns:
            pandas.DataFrame
        """
        session = MarketSession()
        try:
            required_models = self._determine_required_models(filters, sort_by, columns)

            q = session.query(Ticker)

            # Prepare aliases
            fr = aliased(FinancialRatio)
            etf = aliased(ETFInfo)
            rat = aliased(Rating)
            an = aliased(AnalystRecommendation)
            pts = aliased(PriceTargetSummary)

            # Join sequences - join directly to tables first, then use subqueries in WHERE
            if FinancialRatio in required_models:
                q = q.outerjoin(fr, fr.ticker_id == Ticker.id)

            if ETFInfo in required_models:
                q = q.outerjoin(etf, etf.ticker_id == Ticker.id)

            if Rating in required_models:
                q = q.outerjoin(rat, rat.ticker_id == Ticker.id)

            if AnalystRecommendation in required_models:
                q = q.outerjoin(an, an.ticker_id == Ticker.id)

            if PriceTargetSummary in required_models:
                q = q.outerjoin(pts, pts.ticker_id == Ticker.id)

            # WHERE
            where_clauses = []

            # Add latest date filters for time-series tables (using OR NULL to preserve outer join semantics)
            if FinancialRatio in required_models:
                # Only include records with the latest date for each ticker (or NULL if no match)
                where_clauses.append(
                    or_(
                        fr.date == None,  # NULL from outer join
                        fr.date.in_(
                            session.query(func.max(FinancialRatio.date))
                            .filter(FinancialRatio.ticker_id == Ticker.id)
                            .correlate(Ticker)
                            .scalar_subquery()
                        )
                    )
                )

            if Rating in required_models:
                where_clauses.append(
                    or_(
                        rat.date == None,
                        rat.date.in_(
                            session.query(func.max(Rating.date))
                            .filter(Rating.ticker_id == Ticker.id)
                            .correlate(Ticker)
                            .scalar_subquery()
                        )
                    )
                )

            if AnalystRecommendation in required_models:
                where_clauses.append(
                    or_(
                        an.date == None,
                        an.date.in_(
                            session.query(func.max(AnalystRecommendation.date))
                            .filter(AnalystRecommendation.ticker_id == Ticker.id)
                            .correlate(Ticker)
                            .scalar_subquery()
                        )
                    )
                )

            # Add user-specified filters
            for key, value in filters.items():
                # Handle exclusion filters separately
                is_exclude = key.endswith('_exclude')
                col_key = key[:-8] if is_exclude else key  # Remove '_exclude' suffix

                col = self._resolve_column(col_key, ticker=Ticker, fr=fr, etf=etf, rat=rat, an=an, pts=pts)
                if col is None:
                    continue
                condition = self._parse_filter_condition(col, value, exclude=is_exclude)
                if condition is not None:
                    where_clauses.append(condition)
            if where_clauses:
                q = q.filter(and_(*where_clauses))

            # SELECT projection
            select_cols = self._build_select_columns(columns, filters, ticker=Ticker, fr=fr, etf=etf, rat=rat, an=an, pts=pts)
            if select_cols:
                q = q.with_entities(*select_cols)

            # ORDER BY
            if sort_by:
                order_exprs = []
                for s in sort_by:
                    direction = desc if s.startswith("-") else asc
                    key = s[1:] if s.startswith("-") else s
                    col = self._resolve_column(key, ticker=Ticker, fr=fr, etf=etf, rat=rat, an=an, pts=pts)
                    if col is not None:
                        order_exprs.append(direction(col))
                if order_exprs:
                    q = q.order_by(*order_exprs)

            # LIMIT/OFFSET
            q = q.limit(limit).offset(offset)

            # Execute
            df = pd.read_sql(q.statement, session.bind)
            df = self._format_large_numbers(df)
            return df
        finally:
            try:
                session.close()
            except Exception:
                pass

    # ----------------------------- Internals ----------------------------- #
    def _populate_synonyms(self) -> None:
        """Populate synonyms mapping from model columns and friendly names."""
        def add_model_columns(model: Any) -> None:
            for col in model.__table__.columns:
                # Expose native attribute names directly
                self._synonyms.setdefault(col.key, (model, col.key))

        for m in (Ticker, FinancialRatio, ETFInfo, Rating, AnalystRecommendation, PriceTargetSummary):
            add_model_columns(m)

        # Friendly aliases for common screener names
        aliases: Dict[str, Tuple[Any, str]] = {
            # Ticker convenience
            "market_cap": (Ticker, "market_cap"),
            "avg_volume": (Ticker, "avg_volume"),
            "sector": (Ticker, "sector"),
            "industry": (Ticker, "industry"),
            "sub_industry": (Ticker, "sub_industry"),
            "beta": (Ticker, "beta"),
            "is_actively_trading": (Ticker, "is_actively_trading"),
            "is_adr": (Ticker, "is_adr"),
            "is_fund": (Ticker, "is_fund"),
            "ipo_date": (Ticker, "ipo_date"),
            "earnings_announcement": (Ticker, "earnings_announcement"),
            "shares_outstanding": (Ticker, "shares_outstanding"),
            "pe_ratio": (FinancialRatio, "priceEarningsRatio"),
            "pb_ratio": (FinancialRatio, "priceToBookRatio"),
            "ps_ratio": (FinancialRatio, "priceToSalesRatio"),
            "price_to_book": (FinancialRatio, "priceToBookRatio"),
            "price_to_sales": (FinancialRatio, "priceToSalesRatio"),
            "price_to_cash_flow": (FinancialRatio, "priceCashFlowRatio"),
            "price_to_fcf": (FinancialRatio, "priceToFreeCashFlowsRatio"),
            "price_to_ocf": (FinancialRatio, "priceToOperatingCashFlowsRatio"),
            "peg_ratio": (FinancialRatio, "priceEarningsToGrowthRatio"),
            "roe": (FinancialRatio, "returnOnEquity"),
            "roa": (FinancialRatio, "returnOnAssets"),
            "roic": (FinancialRatio, "returnOnCapitalEmployed"),
            "debt_to_equity": (FinancialRatio, "debtEquityRatio"),
            "current_ratio": (FinancialRatio, "currentRatio"),
            "quick_ratio": (FinancialRatio, "quickRatio"),
            "gross_margin": (FinancialRatio, "grossProfitMargin"),
            "operating_margin": (FinancialRatio, "operatingProfitMargin"),
            "net_margin": (FinancialRatio, "netProfitMargin"),
            "asset_turnover": (FinancialRatio, "assetTurnover"),
            "inventory_turnover": (FinancialRatio, "inventoryTurnover"),
            "interest_coverage": (FinancialRatio, "interestCoverage"),
            "dividend_yield": (FinancialRatio, "dividendYield"),
            "enterprise_value_multiple": (FinancialRatio, "enterpriseValueMultiple"),
            "price_fair_value": (FinancialRatio, "priceFairValue"),
            # ETF
            "expense_ratio": (ETFInfo, "expenseRatio"),
            "assets_under_management": (ETFInfo, "assetsUnderManagement"),
            "holdings_count": (ETFInfo, "holdingsCount"),
            "inception_date": (ETFInfo, "inceptionDate"),
            "nav": (ETFInfo, "nav"),
            # Ratings / analyst
            "rating": (Rating, "rating"),
            "overall_score": (Rating, "overallScore"),
            "analyst_rating": (AnalystRecommendation, "ratingRecommendation"),
            "analyst_rating_score": (AnalystRecommendation, "ratingScore"),
            "price_target_last_month": (PriceTargetSummary, "lastMonthAvgPriceTarget"),
            "price_target_last_quarter": (PriceTargetSummary, "lastQuarterAvgPriceTarget"),
            "price_target_last_year": (PriceTargetSummary, "lastYearAvgPriceTarget"),
        }
        for k, v in aliases.items():
            self._synonyms[k] = v

    def _determine_required_models(
        self,
        filters: Dict[str, Any],
        sort_by: Optional[List[str]],
        columns: Optional[List[str]],
    ) -> Set[Any]:
        required: Set[Any] = {Ticker}

        def add_for_key(k: str) -> None:
            entry = self._synonyms.get(k)
            if entry is not None:
                required.add(entry[0])
                return
            for m in (Ticker, FinancialRatio, ETFInfo, Rating, AnalystRecommendation, PriceTargetSummary):
                if hasattr(m, k):
                    required.add(m)
                    return

        for k in filters.keys():
            add_for_key(k)
        if sort_by:
            for s in sort_by:
                key = s[1:] if s.startswith("-") else s
                add_for_key(key)
        if columns:
            for c in columns:
                add_for_key(c)
        return required

    def _build_latest_refs(self, session, required_models: Set[Any]) -> Dict[Any, Any]:
        latest: Dict[Any, Any] = {}
        if FinancialRatio in required_models:
            latest[FinancialRatio] = (
                session.query(
                    FinancialRatio.ticker_id.label("ticker_id"),
                    func.max(FinancialRatio.date).label("max_date"),
                )
                .group_by(FinancialRatio.ticker_id)
                .subquery()
            )
        if Rating in required_models:
            latest[Rating] = (
                session.query(
                    Rating.ticker_id.label("ticker_id"),
                    func.max(Rating.date).label("max_date"),
                )
                .group_by(Rating.ticker_id)
                .subquery()
            )
        if AnalystRecommendation in required_models:
            latest[AnalystRecommendation] = (
                session.query(
                    AnalystRecommendation.ticker_id.label("ticker_id"),
                    func.max(AnalystRecommendation.date).label("max_date"),
                )
                .group_by(AnalystRecommendation.ticker_id)
                .subquery()
            )
        return latest

    def _resolve_column(self, key: str, **aliases) -> Optional[Any]:
        entry = self._synonyms.get(key)
        if entry is not None:
            model, attr = entry
            model_alias = self._pick_alias(model, **aliases)
            return getattr(model_alias, attr, None)
        for model in (aliases.get("ticker"), aliases.get("fr"), aliases.get("etf"), aliases.get("rat"), aliases.get("an"), aliases.get("pts")):
            if model is None:
                continue
            if hasattr(model, key):
                return getattr(model, key)
        return None

    def _pick_alias(self, model: Any, **aliases) -> Any:
        if model is Ticker:
            return aliases.get("ticker") or Ticker
        if model is FinancialRatio:
            return aliases.get("fr")
        if model is ETFInfo:
            return aliases.get("etf")
        if model is Rating:
            return aliases.get("rat")
        if model is AnalystRecommendation:
            return aliases.get("an")
        if model is PriceTargetSummary:
            return aliases.get("pts")
        return model

    def _parse_filter_condition(self, column: Any, value: Any, exclude: bool = False):
        if isinstance(value, tuple) and len(value) == 2:
            min_val, max_val = value
            if min_val is not None and max_val is not None:
                return and_(column >= min_val, column <= max_val)
            if min_val is not None:
                return column >= min_val
            if max_val is not None:
                return column <= max_val
            return None
        if isinstance(value, list):
            return column.notin_(value) if exclude else column.in_(value)
        if isinstance(value, bool):
            return column != value if exclude else column == value
        if isinstance(value, (int, float)):
            return column != value if exclude else column == value
        if isinstance(value, str):
            return column != value if exclude else column == value
        return None

    def _build_select_columns(
        self,
        columns: Optional[List[str]],
        filters: Dict[str, Any],
        **aliases,
    ) -> List[Any]:
        resolved: List[Any] = []
        if columns is None:
            default_keys = [
                "ticker",
                "sector",
                "industry",
                "price",
                "market_cap",
                "avg_volume",
                "pe_ratio",
            ]
            keys = list(dict.fromkeys(default_keys + list(filters.keys())))
        else:
            keys = columns
        for key in keys:
            col = self._resolve_column(key, **aliases)
            if col is not None:
                resolved.append(col.label(key))
        if not any(getattr(c, "key", None) == "ticker" for c in resolved):
            resolved.insert(0, aliases.get("ticker").ticker.label("ticker"))
        return resolved

    def _format_large_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        df_display = df.copy()
        def _fmt_large(x: Any) -> Any:
            if pd.isna(x):
                return None
            try:
                return f"{int(round(float(x))):,}"
            except Exception:
                return x
        # Likely large numeric columns; format if present
        candidate_cols = [
            "market_cap",
            "assets_under_management",
            "avg_volume",
            "dollar_volume",
            "holdings_count",
            "volume",
        ]
        for col in candidate_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(_fmt_large)
        return df_display

def screener(constraints: str) -> str:
    """
    Screen stocks based on fundamental criteria using natural language.

    Args:
        constraints: Natural language description of screening criteria
            Examples:
            - "Find large-cap tech stocks with PE < 20 and ROE > 15%"
            - "Show profitable food companies with market cap over $5B, sorted by dividend yield"
            - "Mid-cap value stocks with low debt and high margins"

    Returns:
        YAML string with success status and screener results
    """
    try:
        # System prompt with comprehensive interpretation guidelines
        system_prompt = """Parse stock screening criteria into structured format.
        Convert natural language descriptions into specific numeric constraints.

        ⚠️ CRITICAL LIMITATIONS - SNAPSHOT DATA ONLY, NO TIME-SERIES ANALYSIS:

        ❌ UNAVAILABLE - All price-based time-series metrics:
        • Alpha, Sharpe ratio, Sortino ratio (risk-adjusted returns)
        • Volatility, annualized volatility, standard deviation (price variability)
        • Returns over ANY time period (1M, 3M, 6M, 1Y, YTD, annualized)
        • Correlation to any index, sector, or stock
        • Momentum, relative strength, price trends
        • VaR, CVaR, drawdowns, tracking error, information ratio

        ❌ UNAVAILABLE - All growth/change metrics requiring historical comparison:
        • Revenue growth (any period: 1Y, 3Y, 5Y, YoY, QoQ)
        • EPS growth, earnings growth, profit growth
        • Sales growth, EBITDA growth, FCF growth
        • Any metric comparing current vs. historical values
        • Trailing growth rates, forward growth rates

        ✅ AVAILABLE - Current snapshot data only:
        • Beta (single point-in-time estimate)
        • Current financial ratios (P/E, P/B, ROE, margins, debt ratios, etc.)
        • Current market data (market cap, price, volume)
        • Static company info (sector, industry, shares outstanding)

        If the user requests ANY unavailable metrics:
        1. Set them to null/None
        2. DO NOT include them in sort_by
        3. DO NOT include them in columns
        4. DO NOT attempt to approximate them with fundamental metrics
        5. IGNORE any growth-related criteria completely

        This screener EXCLUSIVELY supports point-in-time fundamental snapshot data.

        Example queries:
        - "Find large-cap technology stocks with P/E ratio under 20, ROE above 15%, and beta less than 1.2"
        - "Show profitable healthcare companies with market cap over $5B, sorted by dividend yield, exclude ADRs"
        - "Mid-cap value stocks with low debt-to-equity (under 0.5), high operating margins (over 15%), and actively trading"
        - "Growth stocks in consumer staples with ROE > 20%, gross margin > 30%, beta between 0.8 and 1.5, not funds"
        - "High dividend defensive stocks: dividend yield above 3%, beta under 1.0, current ratio above 1.5, shares outstanding over 100M"

        For percentages, ALWAYS convert to decimals (15% → 0.15, 3% → 0.03).
        For dollar amounts, use full numbers (1B → 1000000000, 5M → 5000000).

        **CRITICAL - Sector/Industry Naming Conventions:**

        • EXACT sector names (use these EXACTLY as written):
          - equity_sector_communication_services
          - equity_sector_consumer_discretionary
          - equity_sector_consumer_staples
          - equity_sector_energy
          - equity_sector_financials
          - equity_sector_health_care (NOT healthcare!)
          - equity_sector_industrials
          - equity_sector_information_technology (NOT just technology!)
          - equity_sector_materials
          - equity_sector_real_estate
          - equity_sector_utilities

        • Industry names use underscores and full names:
          - REITs → "diversified_reits", "specialized_reits", "mortgage_reits"
          - Banks → "banks", "regional_banks", "diversified_banks"
          - Technology → "software", "semiconductors_and_semiconductor_equipment", "it_services"
          - Healthcare → "biotechnology", "pharmaceuticals", "health_care_equipment_and_supplies"

        • Sub-industries also use underscores (e.g., "semiconductors", "beverages", "food_products")

        • "Defensive" stocks are NOT a sector - use: equity_sector_consumer_staples, equity_sector_utilities, equity_sector_health_care

        **CRITICAL - ETF Identification:**
        • To find ETFs: set sector = "etf" (NOT is_fund = True!)
        • is_fund = True includes MLPs, BDCs, closed-end funds, REITs (NOT traditional ETFs)
        • ETF industries: "equity_etfs", "fixed_income_etfs", "commodity_etfs", "alternative_etfs", "cryptocurrency_etfs"
        • Example: "Show ETFs" → sector: "etf"

        **CRITICAL - Include vs. Exclude:**
        • Use "sector", "industry", "sub_industry" fields for stocks TO INCLUDE
        • Use "sector_exclude", "industry_exclude", "sub_industry_exclude" for stocks TO EXCLUDE
        • When query says "exclude X" or "avoid Y" → use the _exclude fields
        • Examples:
          - "Exclude REITs and banks" → industry_exclude: ["diversified_reits", "banks"]
          - "Only tech stocks" → industry: ["software", "semiconductors_and_semiconductor_equipment"]
          - "Show ETFs" → sector: "etf"

        Sort descending with "-" prefix (e.g., ["-market_cap"], ["-dividend_yield"]).

        Extract ALL relevant criteria from the query, but ONLY use supported fundamental metrics.
        """

        # Parse natural language to structured constraints
        parsed = parse_with_gpt(constraints, ScreenerConstraints, system_prompt)

        # Debug: Print parsed constraints
        print("\n" + "="*80)
        print("STOCK SCREENER DEBUG - Parsed Constraints:")
        print("="*80)
        print(f"Original query: {constraints}")
        print("\nParsed constraints (non-null values only):")
        for field, value in parsed.model_dump(exclude_none=True).items():
            print(f"  {field}: {value}")
        print("="*80 + "\n")

        # Build criteria dictionary for StockScreener
        criteria_dict = {}

        # Helper to add range filter
        def add_range(key: str, min_val: Optional[float], max_val: Optional[float]):
            if min_val is not None or max_val is not None:
                criteria_dict[key] = (min_val, max_val)

        # Add all valuation filters
        add_range("market_cap", parsed.market_cap_min, parsed.market_cap_max)
        add_range("avg_volume", parsed.avg_volume_min, parsed.avg_volume_max)
        add_range("pe_ratio", parsed.pe_ratio_min, parsed.pe_ratio_max)
        add_range("pb_ratio", parsed.pb_ratio_min, parsed.pb_ratio_max)
        add_range("ps_ratio", parsed.ps_ratio_min, parsed.ps_ratio_max)
        add_range("price_to_cash_flow", parsed.price_to_cash_flow_min, parsed.price_to_cash_flow_max)
        add_range("price_to_fcf", parsed.price_to_fcf_min, parsed.price_to_fcf_max)
        add_range("price_to_ocf", parsed.price_to_ocf_min, parsed.price_to_ocf_max)
        add_range("peg_ratio", parsed.peg_ratio_min, parsed.peg_ratio_max)
        add_range("enterprise_value_multiple", parsed.enterprise_value_multiple_min, parsed.enterprise_value_multiple_max)
        add_range("price_fair_value", parsed.price_fair_value_min, parsed.price_fair_value_max)
        add_range("dividend_yield", parsed.dividend_yield_min, parsed.dividend_yield_max)

        # Add profitability filters
        add_range("roe", parsed.roe_min, parsed.roe_max)
        add_range("roa", parsed.roa_min, parsed.roa_max)
        add_range("roic", parsed.roic_min, parsed.roic_max)
        add_range("gross_margin", parsed.gross_margin_min, parsed.gross_margin_max)
        add_range("operating_margin", parsed.operating_margin_min, parsed.operating_margin_max)
        add_range("net_margin", parsed.net_margin_min, parsed.net_margin_max)

        # Add financial health filters
        add_range("debt_to_equity", parsed.debt_to_equity_min, parsed.debt_to_equity_max)
        add_range("current_ratio", parsed.current_ratio_min, parsed.current_ratio_max)
        add_range("quick_ratio", parsed.quick_ratio_min, parsed.quick_ratio_max)
        add_range("interest_coverage", parsed.interest_coverage_min, parsed.interest_coverage_max)

        # Add efficiency filters
        add_range("asset_turnover", parsed.asset_turnover_min, parsed.asset_turnover_max)
        add_range("inventory_turnover", parsed.inventory_turnover_min, parsed.inventory_turnover_max)

        # Add ETF-specific filters
        add_range("expense_ratio", parsed.expense_ratio_min, parsed.expense_ratio_max)
        add_range("assets_under_management", parsed.assets_under_management_min, parsed.assets_under_management_max)
        add_range("holdings_count", parsed.holdings_count_min, parsed.holdings_count_max)

        # Add rating filters
        add_range("overall_score", parsed.overall_score_min, parsed.overall_score_max)
        add_range("analyst_rating_score", parsed.analyst_rating_score_min, parsed.analyst_rating_score_max)

        # Add price target filters
        add_range("price_target_last_month", parsed.price_target_last_month_min, parsed.price_target_last_month_max)
        add_range("price_target_last_quarter", parsed.price_target_last_quarter_min, parsed.price_target_last_quarter_max)
        add_range("price_target_last_year", parsed.price_target_last_year_min, parsed.price_target_last_year_max)

        # Add classification filters (include)
        if parsed.sector is not None:
            criteria_dict["sector"] = parsed.sector
        if parsed.industry is not None:
            criteria_dict["industry"] = parsed.industry
        if parsed.sub_industry is not None:
            criteria_dict["sub_industry"] = parsed.sub_industry

        # Add classification filters (exclude)
        if parsed.sector_exclude is not None:
            criteria_dict["sector_exclude"] = parsed.sector_exclude
        if parsed.industry_exclude is not None:
            criteria_dict["industry_exclude"] = parsed.industry_exclude
        if parsed.sub_industry_exclude is not None:
            criteria_dict["sub_industry_exclude"] = parsed.sub_industry_exclude

        # Add company profile filters
        add_range("beta", parsed.beta_min, parsed.beta_max)
        add_range("shares_outstanding", parsed.shares_outstanding_min, parsed.shares_outstanding_max)
        if parsed.is_actively_trading is not None:
            criteria_dict["is_actively_trading"] = parsed.is_actively_trading
        if parsed.is_adr is not None:
            criteria_dict["is_adr"] = parsed.is_adr
        if parsed.is_fund is not None:
            criteria_dict["is_fund"] = parsed.is_fund

        # Add display options
        criteria_dict["limit"] = parsed.limit
        criteria_dict["offset"] = parsed.offset
        if parsed.sort_by is not None:
            criteria_dict["sort_by"] = parsed.sort_by
        if parsed.columns is not None:
            criteria_dict["columns"] = parsed.columns

        # Execute screen
        df = StockScreener().screen(**criteria_dict)

        # Debug: Print results summary
        print("\n" + "="*80)
        print("STOCK SCREENER DEBUG - Results Summary:")
        print("="*80)
        print(f"Total results found: {len(df)}")
        if len(df) > 0:
            print(f"Columns: {list(df.columns)}")
            print(f"\nFirst 3 results:")
            print(df.head(3).to_string())
        else:
            print("No results found - query may be too restrictive or data may be missing")
        print("="*80 + "\n")

        result = {
            "success": True,
            "data": df.to_dict('records')
        }
        return yaml.dump(result, default_flow_style=False)
    except Exception as e:
        result = {
            "success": False,
            "error": f"Stock screening failed: {str(e)}"
        }
        return yaml.dump(result, default_flow_style=False)

# Tool Schema Constants
STOCK_SCREENER_DESCRIPTION = (
    "⚠️ SNAPSHOT DATA ONLY - NO TIME-SERIES OR GROWTH METRICS ⚠️\n"
    "\nScreen stocks based on CURRENT FUNDAMENTAL DATA using natural language.\n"
    "\n**CRITICAL LIMITATIONS - This tool provides POINT-IN-TIME data only:**"
    "\n\n❌ UNAVAILABLE - No time-series analysis:"
    "\n  • Alpha, Sharpe ratio, Sortino ratio, volatility, standard deviation"
    "\n  • Returns over ANY period (1M, 3M, 6M, 1Y, YTD, annualized)"
    "\n  • Momentum, correlation, price trends, drawdowns"
    "\n  • Revenue growth, EPS growth, earnings growth (any period)"
    "\n  • Sales growth, profit growth, EBITDA growth, FCF growth"
    "\n  • ANY metric requiring historical comparison or growth rates"
    "\n\n✓ AVAILABLE - Current snapshot metrics only:"
    "\n  • Beta (point-in-time estimate)"
    "\n  • Current valuation ratios (P/E, P/B, P/S, PEG, EV/EBITDA, dividend yield)"
    "\n  • Current profitability (ROE, ROA, ROIC, margins)"
    "\n  • Current financial health (debt ratios, liquidity ratios)"
    "\n  • Static attributes (sector, industry, market cap, shares outstanding)"
    "\n\n**Workflow for time-series metrics:**"
    "\n  1. Use stock_screener to filter by current fundamentals (ROE, margins, debt, beta)"
    "\n  2. Get the resulting ticker list"
    "\n  3. THEN use separate tools for growth/returns/volatility analysis on those tickers"
    "\n\n**Supported Criteria (all current values):**"
    "\n  • Valuation: market cap, avg volume, P/E, P/B, P/S, PEG, EV/EBITDA, price/FCF, dividend yield"
    "\n  • Profitability: ROE, ROA, ROIC, gross/operating/net margins"
    "\n  • Financial Health: debt-to-equity, current/quick ratio, interest coverage"
    "\n  • Efficiency: asset turnover, inventory turnover"
    "\n  • Classification: sector, industry, sub_industry"
    "\n  • Company Profile: beta, is_actively_trading, is_adr, shares_outstanding"
    "\n  • ETF Filters: Use sector='etf' to find ETFs (NOT is_fund). ETF-specific: expense ratio, AUM, holdings count"
    "\n  • Ratings: analyst ratings, price targets"
    "\n  • Display: limit, offset, sort_by, columns"
    "\n\n**Examples:**"
    "\n  • stock_screener(constraints='Find large-cap tech stocks with PE ratio under 20 and ROE above 15%')"
    "\n  • stock_screener(constraints='Show profitable food companies with market cap over $5B, sorted by dividend yield')"
    "\n  • stock_screener(constraints='Mid-cap value stocks with low debt and high margins')"
    "\n  • stock_screener(constraints='High dividend stocks in healthcare sector with strong balance sheets')"
    "\n  • stock_screener(constraints='Stocks with ROE > 20%, operating margin > 15%, beta < 1.0, limit 20 results')"
    "\n\n**Tips:**"
    "\n  • Use descriptive terms: 'large-cap' ($10B+), 'mid-cap' ($2-10B), 'small-cap' (<$2B)"
    "\n  • Percentages work: 'ROE > 15%', 'dividend yield above 3%'"
    "\n  • Natural comparisons: 'PE < 20', 'debt-to-equity under 0.5'"
    "\n  • Sorting: 'sorted by market cap', 'order by dividend yield descending'"
    "\n  • Result control: 'show 50 results', 'limit 20'"
    "\n  • DO NOT request growth rates, returns, or any time-series metrics"
)

STOCK_SCREENER_PARAMETERS = {
    "type": "object",
    "properties": {
        "constraints": {
            "type": "string",
            "description": (
                "Natural language description of stock screening criteria using CURRENT SNAPSHOT DATA ONLY. "
                "⚠️ NO TIME-SERIES METRICS: DO NOT include revenue growth, EPS growth, earnings growth, "
                "sales growth, returns (any period), Sharpe ratio, volatility, momentum, correlation, "
                "alpha, or ANY metric requiring historical comparison. "
                "✓ SNAPSHOT METRICS ONLY: Use P/E, P/B, ROE, ROA, ROIC, margins, debt ratios, market cap, "
                "beta, sector, industry, dividend yield, current ratios. "
                "For growth/time-series analysis, first screen by current fundamentals, then analyze tickers separately. "
                "Examples: 'large-cap tech stocks with PE < 20 and ROE > 15%', "
                "'profitable dividend stocks sorted by yield', "
                "'companies with strong current margins and low debt'."
            )
        }
    },
    "required": ["constraints"],
    "additionalProperties": False
}

STOCK_SCREENER_TOOL = {
    "name": "stock_screener",
    "description": STOCK_SCREENER_DESCRIPTION,
    "parameters": STOCK_SCREENER_PARAMETERS,
    "function": screener,
}


if __name__ == "__main__":
    # Test queries to validate parsing and debugging
    test_queries = [
        # Test 1: Exclusion logic with low beta defensive stocks
        "Find large-cap defensive stocks with beta below 0.7, ROE above 15%, and operating margin above 20%. Exclude REITs, banks, and utilities. Limit 15 results.",

        # Test 2: Multi-sector tech screen with valuation constraints
        "Show mid to large-cap technology and software companies with PE ratio under 25, gross margin above 60%, and debt-to-equity below 0.5. Limit 20 results sorted by market cap.",

        # Test 3: High-quality dividend stocks with exclusions
        "Find dividend-paying stocks with yield above 2.5%, current ratio above 1.5, ROE above 12%, and beta between 0.5 and 1.0. Exclude financials and real estate sectors. Limit 10 results.",

        # Test 4: Growth stocks with profitability filters
        "Large-cap growth stocks in healthcare and consumer discretionary with ROE above 20%, net margin above 15%, and PEG ratio below 2.0. Exclude biotechnology. Limit 12 results.",

        # Test 5: Value stocks with balance sheet strength
        "Mid-cap value stocks with PE under 15, price-to-book below 3, current ratio above 2, debt-to-equity below 0.3, and ROE above 10%. Limit 25 results sorted by ROE descending.",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'#'*80}")
        print(f"TEST QUERY {i}/{len(test_queries)}")
        print(f"{'#'*80}\n")
        result = screener(constraints=query)
        print(f"\n{'='*80}\n")

        # Small pause between queries for readability
        import time
        if i < len(test_queries):
            time.sleep(0.5)