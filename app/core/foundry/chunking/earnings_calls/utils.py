"""
Utility functions for earnings call chunking.
"""

from __future__ import annotations

import inspect

from chonkie import RecursiveLevel


def mk_recursive_level(seps=None, whitespace=False, include_delim=None):
    """
    Create a RecursiveLevel with version-agnostic parameter handling.

    Chonkie's RecursiveLevel has evolved across versions with different
    parameter names. This function inspects the signature and uses the
    appropriate parameter names for compatibility.

    Args:
        seps: Separator(s) for splitting. None allows whitespace-only splitting.
        whitespace: Whether to allow whitespace splitting.
        include_delim: Whether to include delimiters in output.

    Returns:
        A configured RecursiveLevel instance.
    """
    params = inspect.signature(RecursiveLevel).parameters
    kwargs = {}

    if seps is None:
        # Allow whitespace-only splitting without delimiters.
        pass
    elif "delim" in params:
        kwargs["delim"] = seps
    elif "delims" in params:
        kwargs["delims"] = seps
    elif "separators" in params:
        kwargs["separators"] = seps
    elif "separator" in params:
        kwargs["separator"] = seps
    else:
        # Last resort: positional
        try:
            if "whitespace" in params:
                return RecursiveLevel(seps, whitespace=whitespace)
            return RecursiveLevel(seps)
        except TypeError:
            return RecursiveLevel(seps)

    if "whitespace" in params:
        kwargs["whitespace"] = whitespace

    if "include_delim" in params:
        kwargs["include_delim"] = include_delim
    elif "include_separator" in params:
        kwargs["include_separator"] = include_delim
    elif "keep_separator" in params:
        kwargs["keep_separator"] = include_delim

    try:
        return RecursiveLevel(**kwargs)
    except TypeError:
        # Drop include_* if unsupported in this version
        kwargs.pop("include_delim", None)
        kwargs.pop("include_separator", None)
        kwargs.pop("keep_separator", None)
        return RecursiveLevel(**kwargs)
