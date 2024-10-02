"""Data Module."""

from __future__ import annotations

import sys
from abc import ABC
from typing import Any, Iterable

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from pydantic import BaseModel, model_validator


class DataError(TypedDict):
    """Data error type."""

    type: str
    message: str


class DataWrapper(dict):
    """Special type of dictionary that runs callables and stores exceptions.
    Values can be callables or any other type. Callables are evaluated when accessed.
    If an exception occurs, the exception is stored in the `errors` dictionary."""

    def __init__(self, mapping: dict | None = None, /, **kwargs):
        self.errors: dict = {}

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
        """When `value` is a callable, return `(value(), None)` or `(None, exception)` if an exception occurs,
        Return `(value, None)` if `value` is not a callable.

        :Example:

        .. code-block:: python

            DataWrapper.maybe(lambda: 1)
            (1, None)
            DataWrapper.maybe(lambda: 1 / 0)
            (None, ZeroDivisionError('division by zero'))

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
    """Base class for all data items.

    Implements a model validator that wraps the data in a `DataWrapper` and returns the wrapped data with errors.

    :Example:

    .. code-block:: python

        class MyDataItem(BaseDataItem):
            data: int
            data_callable: int

        item = MyDataItem({"data": 1, "data_callable": lambda: 1 / 0})
        print(item)
        # MyDataItem data=1 data_callable=None
        print(item.errors)
        # {'data_callable': {'type': 'ZeroDivisionError', 'message': 'division by zero'}}
    """

    errors: dict[Any, DataError] = {}

    @model_validator(mode="before")
    @classmethod
    def _run_callables(cls, data: Any) -> Any:
        """Wrap the data in a DataWrapper, i.e. evaluate callables and store errors if they occur."""
        wrapped = DataWrapper(data)
        return {**wrapped, "errors": wrapped.errors}


class DataSink(ABC):
    """Data sink protocol.

    Base class used to define the interface for data sinks."""

    def write(self, data: Iterable[dict | BaseModel]) -> None:
        """Write data to the sink."""
        raise NotImplementedError
