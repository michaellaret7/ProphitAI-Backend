"""Tests for BaseUpdater safe type conversions, counters, and timing.

A concrete subclass stubs the abstract methods so we can instantiate
BaseUpdater and exercise its utility methods in isolation.
"""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from prophitai_data.jobs.base import BaseUpdater


# ================================
# --> Helper funcs
# ================================

class _ConcreteUpdater(BaseUpdater):
    """Minimal concrete subclass for testing BaseUpdater utilities."""

    def run(self, **kwargs) -> Dict[str, Any]:
        return {}

    def _get_items_to_update(self) -> List:
        return []

    def _process_single_item(self, item) -> int:
        return 0


def _updater(name: str = "Test Job") -> _ConcreteUpdater:
    """Factory shortcut."""
    return _ConcreteUpdater(job_name=name)


# ================================
# --> Tests: safe type conversions
# ================================

class TestSafeDecimal:
    """BaseUpdater.safe_decimal static method."""

    def test_valid_number(self):
        """A numeric string converts to Decimal."""
        result = _updater().safe_decimal("123.45")
        assert result == Decimal("123.45")

    def test_none_returns_none(self):
        """None input returns None."""
        assert _updater().safe_decimal(None) is None

    def test_invalid_string(self):
        """Non-numeric string returns None."""
        assert _updater().safe_decimal("not_a_number") is None

    def test_nan_returns_decimal_nan(self):
        """float NaN converts to Decimal('NaN') (not None) since Decimal accepts it."""
        result = _updater().safe_decimal(float("nan"))
        # Reason: Decimal(str(float('nan'))) => Decimal('NaN') which is valid
        assert result is not None
        assert result.is_nan()


class TestSafeFloat:
    """BaseUpdater.safe_float static method."""

    def test_valid_number(self):
        """A numeric string converts to float."""
        assert _updater().safe_float("3.14") == pytest.approx(3.14)

    def test_none_returns_none(self):
        """None input returns None."""
        assert _updater().safe_float(None) is None

    def test_empty_string_returns_none(self):
        """Empty string is treated as missing and returns None."""
        assert _updater().safe_float("") is None

    def test_na_string_returns_none(self):
        """'N/A' sentinel is treated as missing and returns None."""
        assert _updater().safe_float("N/A") is None

    def test_nan_returns_float_nan(self):
        """'nan' string converts to float nan (float('nan') is valid)."""
        result = _updater().safe_float("nan")
        # Reason: float("nan") succeeds — safe_float returns it as-is
        assert result is not None
        assert math.isnan(result)

    def test_inf_returns_float_inf(self):
        """'inf' string converts to float inf."""
        result = _updater().safe_float("inf")
        assert result is not None
        assert math.isinf(result)


class TestSafeInt:
    """BaseUpdater.safe_int static method."""

    def test_valid_number(self):
        """A numeric string converts to int."""
        assert _updater().safe_int("42") == 42

    def test_none_returns_none(self):
        """None input returns None."""
        assert _updater().safe_int(None) is None

    def test_invalid_string(self):
        """Non-numeric string returns None."""
        assert _updater().safe_int("abc") is None


class TestSafeDate:
    """BaseUpdater.safe_date static method."""

    def test_valid_string(self):
        """'YYYY-MM-DD' string converts to a date object."""
        result = _updater().safe_date("2024-06-15")
        assert result == date(2024, 6, 15)

    def test_none_returns_none(self):
        """None input returns None."""
        assert _updater().safe_date(None) is None

    def test_invalid_string(self):
        """Badly formatted string returns None."""
        assert _updater().safe_date("not-a-date") is None

    def test_date_passthrough(self):
        """An existing date object is returned unchanged."""
        d = date(2024, 1, 1)
        assert _updater().safe_date(d) == d

    def test_datetime_passthrough_as_date_subclass(self):
        """A datetime is a date subclass, so isinstance(dt, date) is True first.

        The implementation returns it as-is rather than calling .date().
        """
        dt = datetime(2024, 6, 15, 12, 30)
        result = _updater().safe_date(dt)
        # Reason: isinstance checks date before datetime — returns the datetime unchanged
        assert result == dt


class TestSafeDatetime:
    """BaseUpdater.safe_datetime static method."""

    def test_iso_format(self):
        """ISO string with 'T' separator parses correctly."""
        result = _updater().safe_datetime("2024-06-15T12:30:00")
        assert result == datetime(2024, 6, 15, 12, 30, 0)

    def test_space_separated(self):
        """Space-separated format parses correctly."""
        result = _updater().safe_datetime("2024-06-15 12:30:00")
        assert result == datetime(2024, 6, 15, 12, 30, 0)

    def test_date_only(self):
        """Date-only string parses to midnight datetime."""
        result = _updater().safe_datetime("2024-06-15")
        assert result == datetime(2024, 6, 15, 0, 0, 0)

    def test_none_returns_none(self):
        """None input returns None."""
        assert _updater().safe_datetime(None) is None

    def test_datetime_passthrough(self):
        """An existing datetime object is returned unchanged."""
        dt = datetime(2024, 6, 15, 12, 30)
        assert _updater().safe_datetime(dt) == dt


# ================================
# --> Tests: counters
# ================================

class TestCounters:
    """Thread-safe counter increment and read-back."""

    def test_increment_processed(self):
        """increment_processed adds to the processed counter."""
        u = _updater()
        u.increment_processed(3)
        assert u.processed == 3

    def test_increment_successful(self):
        """increment_successful adds to the successful counter."""
        u = _updater()
        u.increment_successful(2)
        assert u.successful == 2

    def test_increment_errors(self):
        """increment_errors adds to the errors counter."""
        u = _updater()
        u.increment_errors(1)
        assert u.errors == 1

    def test_update_counters_success(self):
        """update_counters with is_error=False and records > 0 increments processed, successful, and total_records."""
        u = _updater()
        u.update_counters(records_affected=5, is_error=False)
        assert u.processed == 1
        assert u.successful == 1
        assert u.total_records == 5
        assert u.errors == 0

    def test_update_counters_error(self):
        """update_counters with is_error=True increments processed and errors only."""
        u = _updater()
        u.update_counters(records_affected=0, is_error=True)
        assert u.processed == 1
        assert u.errors == 1
        assert u.successful == 0
        assert u.total_records == 0

    def test_get_progress(self):
        """get_progress returns a dict reflecting current counter state."""
        u = _updater()
        u.total_items = 10
        u.increment_processed(3)
        u.increment_successful(2)
        u.increment_errors(1)

        progress = u.get_progress()
        assert progress == {
            "total_items": 10,
            "processed": 3,
            "successful": 2,
            "errors": 1,
            "total_records": 0,
        }


# ================================
# --> Tests: timing
# ================================

class TestTiming:
    """start_timer / stop_timer utilities."""

    def test_start_timer_sets_start_time(self):
        """start_timer populates start_time with a float."""
        u = _updater()
        assert u.start_time is None
        u.start_timer()
        assert isinstance(u.start_time, float)

    def test_stop_timer_sets_end_time(self):
        """stop_timer populates end_time with a float."""
        u = _updater()
        u.start_timer()
        u.stop_timer()
        assert isinstance(u.end_time, float)
        assert u.end_time >= u.start_time

    def test_get_duration_without_timer(self):
        """get_duration returns 0.0 when the timer was never started."""
        u = _updater()
        assert u.get_duration() == pytest.approx(0.0)
