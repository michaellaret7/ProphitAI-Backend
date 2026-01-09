"""
Base Updater Abstract Class

This module provides an abstract base class for all database update jobs.
It standardizes common patterns like progress tracking, error handling,
thread-safe counters, and summary reporting.

All domain-specific updaters should inherit from BaseUpdater.
"""
from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypeVar, Generic
import logging
import threading
import time

from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseUpdater(ABC, Generic[T]):
    """
    Abstract base class for all database updater jobs.

    Provides:
    - Thread-safe progress tracking
    - Standardized counters (processed, errors, successful, total_records)
    - Safe type conversion utilities
    - Summary printing
    - Timing utilities

    Subclasses must implement:
    - run(): Main entry point for the update job
    - _get_items_to_update(): Fetch items that need updating
    - _process_single_item(): Process a single item
    """

    def __init__(self, job_name: str = "Update Job"):
        """
        Initialize the base updater.

        Args:
            job_name: Human-readable name for this job (used in logging/summaries)
        """
        self.job_name = job_name
        self.lock = threading.Lock()

        # Progress tracking counters
        self._reset_counters()

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def _reset_counters(self) -> None:
        """Reset all progress counters to initial state."""
        self.total_items = 0
        self.processed = 0
        self.successful = 0
        self.errors = 0
        self.total_records = 0

    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for the update job.

        Returns:
            Dictionary with job results and statistics
        """
        pass

    @abstractmethod
    def _get_items_to_update(self) -> List[T]:
        """
        Fetch the list of items that need to be updated.

        Returns:
            List of items to process
        """
        pass

    @abstractmethod
    def _process_single_item(self, item: T) -> int:
        """
        Process a single item and return count of records affected.

        Args:
            item: The item to process

        Returns:
            Number of records inserted/updated (negative for errors)
        """
        pass

    # =========================================================================
    # THREAD-SAFE COUNTER METHODS
    # =========================================================================

    def increment_processed(self, count: int = 1) -> None:
        """Thread-safe increment of processed counter."""
        with self.lock:
            self.processed += count

    def increment_successful(self, count: int = 1) -> None:
        """Thread-safe increment of successful counter."""
        with self.lock:
            self.successful += count

    def increment_errors(self, count: int = 1) -> None:
        """Thread-safe increment of error counter."""
        with self.lock:
            self.errors += count

    def add_records(self, count: int) -> None:
        """Thread-safe addition to total records counter."""
        with self.lock:
            self.total_records += count

    def update_counters(
        self,
        records_affected: int,
        is_error: bool = False
    ) -> None:
        """
        Thread-safe update of all relevant counters after processing an item.

        Args:
            records_affected: Number of records inserted/updated
            is_error: Whether this item resulted in an error
        """
        with self.lock:
            self.processed += 1

            if is_error:
                self.errors += 1
            elif records_affected > 0:
                self.successful += 1
                self.total_records += records_affected

    def get_progress(self) -> Dict[str, int]:
        """
        Get current progress in a thread-safe manner.

        Returns:
            Dictionary with current counter values
        """
        with self.lock:
            return {
                'total_items': self.total_items,
                'processed': self.processed,
                'successful': self.successful,
                'errors': self.errors,
                'total_records': self.total_records
            }

    # =========================================================================
    # SAFE TYPE CONVERSION UTILITIES
    # =========================================================================

    @staticmethod
    def safe_decimal(value: Any) -> Optional[Decimal]:
        """
        Convert value to Decimal safely.

        Args:
            value: Value to convert

        Returns:
            Decimal or None if conversion fails
        """
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return None

    @staticmethod
    def safe_float(value: Any) -> Optional[float]:
        """
        Convert value to float safely.

        Args:
            value: Value to convert

        Returns:
            float or None if conversion fails
        """
        if value is None or value == '' or value == 'N/A':
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_int(value: Any) -> Optional[int]:
        """
        Convert value to int safely.

        Args:
            value: Value to convert

        Returns:
            int or None if conversion fails
        """
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_date(date_string: Any) -> Optional[date]:
        """
        Convert string to date safely.

        Args:
            date_string: Date string in YYYY-MM-DD format

        Returns:
            date object or None if conversion fails
        """
        if not date_string:
            return None
        try:
            if isinstance(date_string, date):
                return date_string
            if isinstance(date_string, datetime):
                return date_string.date()
            if isinstance(date_string, str):
                return datetime.strptime(date_string, '%Y-%m-%d').date()
            return None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_datetime(datetime_string: Any) -> Optional[datetime]:
        """
        Convert string to datetime safely.

        Handles multiple formats:
        - ISO format with T separator
        - Space-separated format
        - Date-only format

        Args:
            datetime_string: Datetime string

        Returns:
            datetime object or None if conversion fails
        """
        if not datetime_string:
            return None
        if isinstance(datetime_string, datetime):
            return datetime_string

        try:
            # Handle different datetime formats from APIs
            if isinstance(datetime_string, str):
                if 'T' in datetime_string:
                    # ISO format
                    return datetime.fromisoformat(
                        datetime_string.replace('Z', '+00:00')
                    )
                elif ' ' in datetime_string:
                    # Space separated format
                    return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')
                else:
                    # Date only format
                    return datetime.strptime(datetime_string, '%Y-%m-%d')
        except (TypeError, ValueError, AttributeError):
            pass

        return None

    # =========================================================================
    # TIMING UTILITIES
    # =========================================================================

    def start_timer(self) -> None:
        """Start the job timer."""
        self.start_time = time.time()

    def stop_timer(self) -> None:
        """Stop the job timer."""
        self.end_time = time.time()

    def get_duration(self) -> float:
        """
        Get the job duration in seconds.

        Returns:
            Duration in seconds, or 0 if timer not started
        """
        if self.start_time is None:
            return 0.0

        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def get_average_time_per_item(self) -> float:
        """
        Get average processing time per item.

        Returns:
            Average seconds per item, or 0 if no items processed
        """
        if self.processed == 0:
            return 0.0
        return self.get_duration() / self.processed

    # =========================================================================
    # PROGRESS REPORTING
    # =========================================================================

    def log_progress(self, interval: int = 50) -> None:
        """
        Log progress if processed count is at interval boundary.

        Args:
            interval: Report every N items processed
        """
        with self.lock:
            if self.processed > 0 and self.processed % interval == 0:
                pct = (self.processed / self.total_items * 100) if self.total_items > 0 else 0
                logger.info(
                    f"{self.job_name} Progress: {self.processed}/{self.total_items} "
                    f"({pct:.1f}%) - Success: {self.successful}, Errors: {self.errors}"
                )

    def print_progress(self, interval: int = 50) -> None:
        """
        Print progress to stdout if processed count is at interval boundary.

        Args:
            interval: Report every N items processed
        """
        with self.lock:
            if self.processed > 0 and self.processed % interval == 0:
                pct = (self.processed / self.total_items * 100) if self.total_items > 0 else 0
                print(
                    f"Progress: {self.processed}/{self.total_items} "
                    f"({pct:.1f}%) - Success: {self.successful}, Errors: {self.errors}"
                )

    # =========================================================================
    # SUMMARY PRINTING
    # =========================================================================

    def print_summary(self) -> None:
        """Print a standardized summary of the update job."""
        duration = self.get_duration()
        avg_time = self.get_average_time_per_item()

        print(f"\n{'='*70}")
        print(f"{self.job_name.upper()} SUMMARY")
        print(f"{'='*70}")
        print(f"Total items: {self.total_items:,}")
        print(f"Processed: {self.processed:,}")
        print(f"Successful: {self.successful:,}")
        print(f"Errors: {self.errors:,}")
        print(f"Total records inserted/updated: {self.total_records:,}")
        print(f"Time taken: {duration:.2f} seconds")
        if self.processed > 0:
            print(f"Average time per item: {avg_time:.3f} seconds")
            print(f"Throughput: {self.processed/duration:.2f} items/second")
        print(f"{'='*70}\n")

    def get_summary_dict(self) -> Dict[str, Any]:
        """
        Get summary statistics as a dictionary.

        Returns:
            Dictionary with all summary statistics
        """
        duration = self.get_duration()
        return {
            'job_name': self.job_name,
            'total_items': self.total_items,
            'processed': self.processed,
            'successful': self.successful,
            'errors': self.errors,
            'total_records': self.total_records,
            'duration_seconds': duration,
            'avg_time_per_item': self.get_average_time_per_item(),
            'throughput': self.processed / duration if duration > 0 else 0,
            'success_rate': self.successful / self.processed if self.processed > 0 else 0,
            'completed_at': get_current_utc_time().isoformat()
        }

    # =========================================================================
    # ERROR HANDLING UTILITIES
    # =========================================================================

    def log_error(self, item_identifier: str, error: Exception) -> None:
        """
        Log an error with context.

        Args:
            item_identifier: String identifying the item that failed
            error: The exception that occurred
        """
        logger.error(f"{self.job_name} - Error processing {item_identifier}: {str(error)}")

    def log_item_error(self, item_identifier: str, message: str) -> None:
        """
        Log an item-level error message.

        Args:
            item_identifier: String identifying the item
            message: Error message
        """
        logger.warning(f"{self.job_name} - {item_identifier}: {message}")


