"""Tests for serialize_sqlalchemy_obj in prophitai_data.db.utils.

Uses MagicMock to simulate a SQLAlchemy model instance without requiring
a real database connection or ORM metadata.
"""

from datetime import datetime, date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from prophitai_data.db.utils import serialize_sqlalchemy_obj


# ================================
# --> Helper funcs
# ================================

def _make_sa_mock(column_values: dict) -> MagicMock:
    """Build a MagicMock that looks like a SQLAlchemy mapped instance.

    Args:
        column_values: mapping of column_name -> Python value
    """
    obj = MagicMock()

    # Reason: serialize_sqlalchemy_obj iterates obj.__table__.columns
    columns = []
    for name in column_values:
        col = MagicMock()
        col.name = name
        columns.append(col)
    obj.__table__ = MagicMock()
    obj.__table__.columns = columns

    # Reason: getattr(obj, column.name) must return the test value
    for name, value in column_values.items():
        setattr(obj, name, value)

    return obj


# ================================
# --> Tests
# ================================

class TestSerializeSqlalchemyObj:
    """Validate type coercion performed by serialize_sqlalchemy_obj."""

    def test_none_input_returns_none(self):
        """Passing None returns None immediately."""
        assert serialize_sqlalchemy_obj(None) is None

    def test_none_value_preserved(self):
        """A column whose value is None stays None in the output dict."""
        obj = _make_sa_mock({"notes": None})
        result = serialize_sqlalchemy_obj(obj)
        assert result["notes"] is None

    def test_datetime_to_isoformat(self):
        """datetime values are serialised via .isoformat()."""
        dt = datetime(2024, 6, 15, 12, 30, 0)
        obj = _make_sa_mock({"created_at": dt})
        result = serialize_sqlalchemy_obj(obj)
        assert result["created_at"] == "2024-06-15T12:30:00"

    def test_date_to_isoformat(self):
        """date values are serialised via .isoformat()."""
        d = date(2024, 6, 15)
        obj = _make_sa_mock({"trade_date": d})
        result = serialize_sqlalchemy_obj(obj)
        assert result["trade_date"] == "2024-06-15"

    def test_decimal_to_float(self):
        """Decimal values are converted to float."""
        obj = _make_sa_mock({"price": Decimal("123.45")})
        result = serialize_sqlalchemy_obj(obj)
        assert result["price"] == pytest.approx(123.45)
        assert isinstance(result["price"], float)

    def test_uuid_to_string(self):
        """UUID values are converted to their string representation."""
        uid = UUID("12345678-1234-5678-1234-567812345678")
        obj = _make_sa_mock({"id": uid})
        result = serialize_sqlalchemy_obj(obj)
        assert result["id"] == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result["id"], str)

    def test_string_unchanged(self):
        """Plain strings pass through without modification."""
        obj = _make_sa_mock({"ticker": "AAPL"})
        result = serialize_sqlalchemy_obj(obj)
        assert result["ticker"] == "AAPL"

    def test_int_unchanged(self):
        """Integers pass through without modification."""
        obj = _make_sa_mock({"volume": 1_000_000})
        result = serialize_sqlalchemy_obj(obj)
        assert result["volume"] == 1_000_000

    def test_multiple_columns(self):
        """All columns are serialised in a single pass."""
        dt = datetime(2024, 1, 1, 0, 0)
        uid = UUID("abcdef01-2345-6789-abcd-ef0123456789")
        obj = _make_sa_mock({
            "id": uid,
            "ticker": "GOOG",
            "price": Decimal("2800.50"),
            "created_at": dt,
            "notes": None,
        })
        result = serialize_sqlalchemy_obj(obj)

        assert isinstance(result["id"], str)
        assert result["ticker"] == "GOOG"
        assert result["price"] == pytest.approx(2800.50)
        assert result["created_at"] == "2024-01-01T00:00:00"
        assert result["notes"] is None
