from __future__ import annotations

from collections import UserDict
from logging import getLogger
from typing import Any, TypedDict

from pydantic import BaseModel

logger = getLogger(__name__)


class DataError(TypedDict):
    """Data error type."""

    type: str
    message: str


class DataWrapper(dict):
    """Special type of dictionary that runs callables and stores exceptions.
    Values can be callables or any other type. Callables are evaluated when accessed.
    When a callable is evaluated, the result is stored in the exceptions dictionary class var.
    If an exception occurs, the exception is stored in the `errors` dictionary."""

    def __init__(self, mapping: dict | None = None, /, **kwargs):
        """Initialize the DataWrapper."""
        self.errors = {}

        if mapping is not None:
            for key, value in mapping.items():
                mapping[key] = self._set_item(key, value)
        else:
            mapping = {}
        if kwargs:
            for key, value in kwargs.items():
                mapping[key] = self._set_item(key, value)

        super().__init__(mapping)

    def __setitem__(self, key: Any, value: Any):
        """Set attribute value, evaluating callables. If an exception occurs, store it in the exceptions dict.

        :param key: The key to set in the dictionary.
        :param value: The value to set in the dictionary.
        """
        maybe_value = self._set_item(key, value)
        super().__setitem__(key, maybe_value)

    def _set_item(self, key, value):
        """Set the value for the given key, evaluating callables."""
        maybe_value, maybe_exception = self.maybe(value)
        if maybe_exception:
            self.errors[key] = DataError(
                **{
                    "type": type(maybe_exception).__name__,
                    "message": str(maybe_exception),
                }
            )
        return maybe_value

    @staticmethod
    def maybe(value: Any) -> tuple[Any | None, None | Exception]:
        """When value is a callable, return (value(), None) or (None, exception) if an exception occurs,
        return (value, None) otherwise.

        :param value: The value to be evaluated. It can be a callable or any other type.
        :return: A tuple containing the evaluated value or None, and an exception or None.
        """
        if callable(value):
            try:
                return value(), None
            except Exception as e:
                return None, e
        return value, None


class BaseDataItem(BaseModel):
    """Base class for all data items."""

    errors: dict[Any, DataError] = {}

    @classmethod
    def wrap(cls, **data: dict) -> BaseDataItem:
        """Create a new instance of the class by wrapping data in a DataWrapper.

        :param data: The data to wrap.
        :return: A new instance of the DataItem class.
        """
        wrapped = DataWrapper(**data)
        wrapped.update(errors=wrapped.errors)
        return cls(**wrapped)
