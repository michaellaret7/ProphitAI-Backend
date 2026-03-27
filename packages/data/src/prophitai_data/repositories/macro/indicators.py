"""Economic indicator data retrieval from the macro database."""

from datetime import date
from typing import Optional

from pandas import DataFrame

from prophitai_data.db.models.macro import EconomicIndicators
from prophitai_data.session import with_session


@with_session('macro')
def get_economic_indicators(
    indicator: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session=None
):
    query = session.query(EconomicIndicators).filter(EconomicIndicators.indicator == indicator)
    if start_date:
        query = query.filter(EconomicIndicators.date >= start_date)
    if end_date:
        query = query.filter(EconomicIndicators.date <= end_date)
    query = query.order_by(EconomicIndicators.date.asc())
    indicators = query.all()

    return DataFrame([
        {
            'indicator': indicator.indicator,
            'date': indicator.date,
            'value': indicator.value
        } for indicator in indicators
    ])
