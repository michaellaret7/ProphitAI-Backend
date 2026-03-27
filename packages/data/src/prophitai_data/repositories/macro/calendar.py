"""Economic calendar data retrieval from the macro database."""

from datetime import date, timedelta
from typing import Optional

from pandas import DataFrame

from prophitai_data.db.models.macro import EconomicCalendar
from prophitai_data.session import with_session


@with_session('macro')
def get_economic_calendar(
    country: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    event: Optional[str] = None,
    session=None
):
    """
    Fetch economic calendar events for a given country.

    Args:
        country: Country code (e.g., "US", "UK", "CA", "FR", "DE", "IT", "JP")
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)
        event: Optional event name filter (partial match, case-insensitive)
        session: Database session (injected by decorator)

    Returns:
        DataFrame with columns: event_id, id (country UUID), event, date, country,
                                currency, actual, previous, estimate, change,
                                change_percentage, impact
    """
    query = session.query(EconomicCalendar).filter(EconomicCalendar.country == country)

    # Add date filters if provided
    if start_date:
        query = query.filter(EconomicCalendar.date >= start_date)
    if end_date:
        # Use < next day to include entire end_date (events through 23:59:59)
        # Reason: Database column is DateTime, so <= date compares against midnight only
        query = query.filter(EconomicCalendar.date < end_date + timedelta(days=1))

    # Add event filter if provided (partial match, case-insensitive)
    if event:
        query = query.filter(EconomicCalendar.event.ilike(f'%{event}%'))

    # Order by date ascending
    query = query.order_by(EconomicCalendar.date.asc())

    events = query.all()

    # Convert to DataFrame
    df = DataFrame([
        {
            'event_id': event.event_id,
            'id': event.id,
            'event': event.event,
            'date': event.date,
            'country': event.country,
            'currency': event.currency,
            'actual': event.actual,
            'previous': event.previous,
            'estimate': event.estimate,
            'change': event.change,
            'change_percentage': event.change_percentage,
            'impact': event.impact
        }
        for event in events
    ])

    return df
