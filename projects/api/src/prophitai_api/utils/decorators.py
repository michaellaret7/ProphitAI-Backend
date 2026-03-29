"""
Decorators for API controller functions.

This module provides reusable decorators for common controller patterns
like error handling, reducing code duplication across the API layer.
"""

from functools import wraps
from fastapi import HTTPException
from typing import Callable, TypeVar, Any
import logging
import asyncio

from prophitai_api.utils.exceptions import BrokerNotConnectedError
from prophitai_api.utils.response_envelope import error_envelope

logger = logging.getLogger(__name__)

T = TypeVar('T')


def handle_controller_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to standardize error handling across all controller functions.

    Converts exceptions to appropriate HTTP responses:
    - HTTPException: Pass through unchanged
    - ValueError: Convert to 400 Bad Request
    - All other exceptions: Convert to 500 Internal Server Error

    Usage:
        @handle_controller_errors
        async def my_controller(...):
            # Business logic here
            # Raise ValueError for validation errors
            # Raise HTTPException for specific HTTP errors
            return response

    Args:
        func: The controller function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Pass through HTTP exceptions unchanged
            raise
        except BrokerNotConnectedError as e:
            logger.info(f"Broker not connected in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=422,
                detail=error_envelope(
                    code=422,
                    message=str(e),
                    errors=[{"reason": "broker_not_connected"}],
                ),
            )
        except ValueError as e:
            # Convert validation errors to 400 Bad Request
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert unexpected errors to 500 Internal Server Error
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except BrokerNotConnectedError as e:
            logger.info(f"Broker not connected in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=422,
                detail=error_envelope(
                    code=422,
                    message=str(e),
                    errors=[{"reason": "broker_not_connected"}],
                ),
            )
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
