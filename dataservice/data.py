from __future__ import annotations

from logging import getLogger
from typing import Any

logger = getLogger(__name__)


class AttrDict(dict):
    """Access dictionary keys as attributes.

    https://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute
    """

    def __init__(self, *args, **kwargs):
        """Initialize the AttrDict.

        :param args: Positional arguments for the dictionary.
        :param kwargs: Keyword arguments for the dictionary.
        """
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class DataWrapper(AttrDict):
    """Special type of dictionary that runs callables and stores exceptions.
    Values can be callables or any other type. Callables are evaluated when accessed.
    When a callable is evaluated, the result is stored in the exceptions dictionary class var.
    If an exception occurs, the exception is stored in the exceptions dictionary.
    Furthermore, keys can be accessed as attributes."""

    exceptions: AttrDict = AttrDict()

    def __init__(self, **kwargs):
        """Initialize the DataWrapper.

        :param kwargs: Keyword arguments for the dictionary.
        """
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def __setattr__(self, key: Any, value: Any):
        """Set attribute value, evaluating callables. If an exception occurs, store it in the exceptions dict.

        :param key: The key to set in the dictionary.
        :param value: The value to set in the dictionary.
        """
        maybe_value, maybe_exception = self.maybe(value)
        if maybe_exception:
            self.exceptions[key] = {
                "type": type(maybe_exception).__name__,
                "message": str(maybe_exception),
            }
        super().__setattr__(key, maybe_value)

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
