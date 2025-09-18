from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union, Set

import pandas as pd
from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import aliased

from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import (
    Ticker,
    FinancialRatio,
    ETFInfo,
    Rating,
    AnalystRecommendation,
    PriceTargetSummary,
)

Numeric = Union[int, float]
Range = Tuple[Optional[Numeric], Optional[Numeric]]

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
            latest_refs = self._build_latest_refs(session, required_models)

            q = session.query(Ticker)

            # Prepare aliases
            fr = aliased(FinancialRatio)
            etf = aliased(ETFInfo)
            rat = aliased(Rating)
            an = aliased(AnalystRecommendation)
            pts = aliased(PriceTargetSummary)

            # Join sequences (include latest subqueries when available)
            if FinancialRatio in required_models:
                fr_latest = latest_refs.get(FinancialRatio)
                if fr_latest is not None:
                    q = q.outerjoin(fr_latest, fr_latest.c.ticker_id == Ticker.id)
                    q = q.outerjoin(fr, and_(fr.ticker_id == Ticker.id, fr.date == fr_latest.c.max_date))
                else:
                    q = q.outerjoin(fr, fr.ticker_id == Ticker.id)

            if ETFInfo in required_models:
                q = q.outerjoin(etf, etf.ticker_id == Ticker.id)

            if Rating in required_models:
                rat_latest = latest_refs.get(Rating)
                if rat_latest is not None:
                    q = q.outerjoin(rat_latest, rat_latest.c.ticker_id == Ticker.id)
                    q = q.outerjoin(rat, and_(rat.ticker_id == Ticker.id, rat.date == rat_latest.c.max_date))
                else:
                    q = q.outerjoin(rat, rat.ticker_id == Ticker.id)

            if AnalystRecommendation in required_models:
                an_latest = latest_refs.get(AnalystRecommendation)
                if an_latest is not None:
                    q = q.outerjoin(an_latest, an_latest.c.ticker_id == Ticker.id)
                    q = q.outerjoin(an, and_(an.ticker_id == Ticker.id, an.date == an_latest.c.max_date))
                else:
                    q = q.outerjoin(an, an.ticker_id == Ticker.id)

            if PriceTargetSummary in required_models:
                q = q.outerjoin(pts, pts.ticker_id == Ticker.id)

            # WHERE
            where_clauses = []
            for key, value in filters.items():
                col = self._resolve_column(key, ticker=Ticker, fr=fr, etf=etf, rat=rat, an=an, pts=pts)
                if col is None:
                    continue
                condition = self._parse_filter_condition(col, value)
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

    def _parse_filter_condition(self, column: Any, value: Any):
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
            return column.in_(value)
        if isinstance(value, bool):
            return column == value
        if isinstance(value, (int, float)):
            return column == value
        if isinstance(value, str):
            return column == value
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



