from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict


class PriceData(BaseModel):
    """Wrapper for price data frames used by calculators.

    The frame should have a DatetimeIndex and columns: 'open','high','low','close','volume'.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    frame: pd.DataFrame


class DividendsData(BaseModel):
    """Wrapper for dividend series.

    Series index is datetime (ex-dividend date) and values are dividend amounts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    series: pd.Series


class FundamentalData(BaseModel):
    """Container for fundamental datasets fetched from the database.

    Stores raw SQLAlchemy rows (arbitrary types allowed) to be consumed by
    factor calculators. We intentionally avoid transformation here to keep
    the data layer simple and non-opinionated.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    income_statements: Any
    balance_sheets: Any
    cash_flow_statements: Any
    financial_ratios: Any
    analyst_estimates: Any


