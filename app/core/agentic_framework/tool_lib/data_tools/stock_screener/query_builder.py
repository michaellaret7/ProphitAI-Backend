"""SQLAlchemy query builder for stock screening."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import aliased

from app.db.core.models.market_data_models import (
    AnalystRecommendation,
    ETFInfo,
    FinancialRatio,
    PriceTargetSummary,
    Rating,
    Ticker,
)

from .models import get_field_synonym_mappings
from .utils import format_screener_results, market_session


class StockScreener:
    """
    High-level stock screener with tuple-based operators and dynamic JOINs.

    - No caching – every call executes a fresh DB query
    - Exposes all available fundamental datapoints present in schemas
    - Joins only the tables needed by active filters, sorts, or selected columns
    """

    def __init__(self) -> None:
        """Initialize screener with field synonym mappings."""
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
        with market_session() as session:
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

            # Reason: Add latest date filters for time-series tables using correlated subqueries.
            # Using == with scalar_subquery ensures only the latest record per ticker is returned.
            # OR NULL preserves outer join semantics for tickers without matching records.
            if FinancialRatio in required_models:
                latest_fr_date = (
                    session.query(func.max(FinancialRatio.date))
                    .filter(FinancialRatio.ticker_id == Ticker.id)
                    .correlate(Ticker)
                    .scalar_subquery()
                )
                where_clauses.append(
                    or_(fr.date == None, fr.date == latest_fr_date)
                )

            if Rating in required_models:
                latest_rat_date = (
                    session.query(func.max(Rating.date))
                    .filter(Rating.ticker_id == Ticker.id)
                    .correlate(Ticker)
                    .scalar_subquery()
                )
                where_clauses.append(
                    or_(rat.date == None, rat.date == latest_rat_date)
                )

            if AnalystRecommendation in required_models:
                latest_an_date = (
                    session.query(func.max(AnalystRecommendation.date))
                    .filter(AnalystRecommendation.ticker_id == Ticker.id)
                    .correlate(Ticker)
                    .scalar_subquery()
                )
                where_clauses.append(
                    or_(an.date == None, an.date == latest_an_date)
                )

            # Add user-specified filters
            for key, value in filters.items():
                # Reason: Handle exclusion filters separately
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
            df = format_screener_results(df)
            return df

    # ----------------------------- Internals ----------------------------- #

    def _populate_synonyms(self) -> None:
        """Populate synonyms mapping from model columns and friendly names."""
        def add_model_columns(model: Any) -> None:
            for col in model.__table__.columns:
                # Reason: Expose native attribute names directly
                self._synonyms.setdefault(col.key, (model, col.key))

        for m in (Ticker, FinancialRatio, ETFInfo, Rating, AnalystRecommendation, PriceTargetSummary):
            add_model_columns(m)

        # Add friendly aliases from mappings
        friendly_aliases = get_field_synonym_mappings()
        for k, v in friendly_aliases.items():
            self._synonyms[k] = v

    # Reason: Default columns used when none specified - must match _build_select_columns
    DEFAULT_SELECT_COLUMNS = [
        "ticker",
        "sector",
        "industry",
        "price",
        "market_cap",
        "avg_volume",
        "pe_ratio",
    ]

    def _determine_required_models(
        self,
        filters: Dict[str, Any],
        sort_by: Optional[List[str]],
        columns: Optional[List[str]],
    ) -> Set[Any]:
        """
        Determine which database models need to be JOINed based on filters, sorting, and columns.

        Args:
            filters: Filter criteria dictionary
            sort_by: Sort fields
            columns: Requested output columns

        Returns:
            Set of model classes that need to be joined
        """
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

        # Reason: When columns is None, default columns are used in _build_select_columns.
        # Must include them here to ensure required tables are JOINed.
        effective_columns = columns if columns else self.DEFAULT_SELECT_COLUMNS
        for c in effective_columns:
            add_for_key(c)

        return required

    def _resolve_column(self, key: str, **aliases) -> Optional[Any]:
        """
        Resolve a column name to a SQLAlchemy column object.

        Args:
            key: Field name to resolve
            **aliases: Model aliases (ticker, fr, etf, rat, an, pts)

        Returns:
            SQLAlchemy column object or None if not found
        """
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
        """
        Pick the appropriate alias for a model.

        Args:
            model: Model class
            **aliases: Model aliases

        Returns:
            Model alias or original model if no alias exists
        """
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
        """
        Parse a filter value into a SQLAlchemy condition.

        Args:
            column: SQLAlchemy column object
            value: Filter value (tuple, list, bool, int, float, or str)
            exclude: If True, negate the condition

        Returns:
            SQLAlchemy condition or None
        """
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
        """
        Build SELECT column list for query.

        Args:
            columns: Explicitly requested columns
            filters: Filter criteria (used to include filtered columns in output)
            **aliases: Model aliases

        Returns:
            List of SQLAlchemy column objects with labels
        """
        resolved: List[Any] = []
        if columns is None:
            # Reason: Use default columns plus any filtered columns
            keys = list(dict.fromkeys(self.DEFAULT_SELECT_COLUMNS + list(filters.keys())))
        else:
            keys = columns
        for key in keys:
            col = self._resolve_column(key, **aliases)
            if col is not None:
                resolved.append(col.label(key))
        # Reason: Ensure ticker column is always present
        if not any(getattr(c, "key", None) == "ticker" for c in resolved):
            resolved.insert(0, aliases.get("ticker").ticker.label("ticker"))
        return resolved
