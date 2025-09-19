"""Simple execution timer decorator.

Prints the time a function takes to run in seconds.

Usage:
    @timer
    def my_function(...):
        ...
"""

from functools import wraps
from time import perf_counter
from typing import Any, Callable


def timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that prints how many seconds the wrapped function took to execute."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_seconds = perf_counter() - start_time
            print(f"{func.__name__} took {elapsed_seconds:.4f} seconds")

    return wrapper


