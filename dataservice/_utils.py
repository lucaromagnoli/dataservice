"""Utility functions for dataservice module."""

from functools import partial
from typing import Callable


def _get_func_name(func: Callable) -> str:
    """Get the name of the function."""
    if isinstance(func, partial):
        if hasattr(func, "keywords"):
            # functools.wraps
            if "wrapped" in func.keywords:
                return func.keywords["wrapped"].__name__
        return func.func.__name__
    elif hasattr(func, "__name__"):
        return func.__name__
    elif hasattr(func, "__class__"):
        return type(func).__name__
    else:
        return str(func)
