"""Watchlist repository functions for watchlist and watchlist item CRUD operations."""

from prophitai_data.db.models.user import *
from sqlalchemy.orm import selectinload
from prophitai_data.session import with_session, with_transaction
from prophitai_shared import get_current_utc_time
from prophitai_data.clients.fmp import FMP_API_DATA


@with_session('user')
def get_user_watchlists(user_id: str, session=None):
    """Get all watchlists for a user with their items."""
    if not user_id:
        raise ValueError("User ID must be provided")

    watchlists = session.query(Watchlist).options(
        selectinload(Watchlist.items)
    ).filter(Watchlist.user_id == user_id).all()

    return [
        {
            'id': str(w.id),
            'name': w.name,
            'creation_date': w.creation_date.isoformat() if w.creation_date else None,
            'updated_date': w.updated_date.isoformat() if w.updated_date else None,
            'items': [
                {
                    'ticker': item.ticker,
                    'price_on_inception': item.price_on_inception,
                    'added_at': item.added_at.isoformat() if item.added_at else None
                }
                for item in w.items
            ]
        }
        for w in watchlists
    ]

@with_session('user')
def get_watchlist_by_id(watchlist_id: str, session=None):
    """Get a single watchlist by ID with its items."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")

    watchlist = session.query(Watchlist).options(
        selectinload(Watchlist.items)
    ).filter(Watchlist.id == watchlist_id).first()

    if not watchlist:
        return None

    return {
        'id': str(watchlist.id),
        'user_id': str(watchlist.user_id),
        'name': watchlist.name,
        'creation_date': watchlist.creation_date.isoformat() if watchlist.creation_date else None,
        'updated_date': watchlist.updated_date.isoformat() if watchlist.updated_date else None,
        'items': [
            {
                'ticker': item.ticker,
                'price_on_inception': item.price_on_inception,
                'added_at': item.added_at.isoformat() if item.added_at else None
            }
            for item in watchlist.items
        ]
    }

@with_transaction('user')
def add_watchlist(user_id: str, name: str, session=None):
    """Create a new watchlist for a user."""
    if not user_id:
        raise ValueError("User ID must be provided")
    if not name:
        raise ValueError("Name must be provided")

    watchlist = Watchlist(user_id=user_id, name=name, creation_date=get_current_utc_time())
    session.add(watchlist)
    session.flush()

    return {
        'id': str(watchlist.id),
        'user_id': str(watchlist.user_id),
        'name': watchlist.name,
        'creation_date': watchlist.creation_date.isoformat() if watchlist.creation_date else None
    }

@with_transaction('user')
def rename_watchlist(watchlist_id: str, name: str, session=None):
    """Rename an existing watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not name:
        raise ValueError("Name must be provided")

    watchlist = session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        return None

    watchlist.name = name
    watchlist.updated_date = get_current_utc_time()

    return {
        'id': str(watchlist.id),
        'name': watchlist.name,
        'updated_date': watchlist.updated_date.isoformat()
    }

@with_transaction('user')
def delete_watchlist(watchlist_id: str, session=None):
    """Delete a watchlist and all its items."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")

    watchlist = session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        return False

    session.delete(watchlist)
    return True

@with_transaction('user')
def add_watchlist_item(watchlist_id: str, ticker: str, session=None):
    """Add a ticker to a watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not ticker:
        raise ValueError("Ticker must be provided")

    fmp = FMP_API_DATA()
    try:
        quote_data = fmp.get_full_quote(ticker)
        price_on_inception = quote_data[0]['price'] if quote_data else None
    except (IndexError, KeyError, Exception):
        price_on_inception = None

    watchlist_item = WatchlistItem(
        watchlist_id=watchlist_id,
        ticker=ticker.upper(),
        price_on_inception=price_on_inception,
        added_at=get_current_utc_time()
    )
    session.add(watchlist_item)
    session.flush()

    return {
        'watchlist_id': str(watchlist_item.watchlist_id),
        'ticker': watchlist_item.ticker,
        'price_on_inception': watchlist_item.price_on_inception,
        'added_at': watchlist_item.added_at.isoformat() if watchlist_item.added_at else None
    }

@with_transaction('user')
def delete_watchlist_item(watchlist_id: str, ticker: str, session=None):
    """Remove a ticker from a watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not ticker:
        raise ValueError("Ticker must be provided")

    watchlist_item = session.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == watchlist_id,
        WatchlistItem.ticker == ticker.upper()
    ).first()

    if not watchlist_item:
        return False

    session.delete(watchlist_item)
    return True
