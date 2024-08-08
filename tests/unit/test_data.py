import pytest

from dataservice.data import BaseDataItem, DataWrapper


class TestItem(BaseDataItem):
    foo: int | None
    bar: int | None


def test_maybe_callable_returns_value():
    d = DataWrapper()
    value, exception = d.maybe(lambda: 1)
    assert value == 1
    assert exception is None


def test_maybe_callable_raises_exception():
    d = DataWrapper()

    def raise_exception():
        raise ValueError("error")

    value, exception = d.maybe(raise_exception)
    assert value is None
    assert isinstance(exception, ValueError)


def test_maybe_non_callable_value():
    d = DataWrapper()
    value, exception = d.maybe(1)
    assert value == 1
    assert exception is None


def test_datawrapper_init_kwargs():
    d = DataWrapper(a=lambda: 1, b=lambda: 1 / 0)
    assert d["a"] == 1
    assert d["b"] is None
    assert d.errors == {
        "b": {"type": "ZeroDivisionError", "message": "division by zero"}
    }


def test_datawrapper_init_dict():
    d = DataWrapper({"a": lambda: 1, "b": lambda: 1 / 0})
    assert d["a"] == 1
    assert d["b"] is None
    assert d.errors == {
        "b": {"type": "ZeroDivisionError", "message": "division by zero"}
    }


def test_datawrapper_is_instance_of_dict():
    d = DataWrapper(a=lambda: 1, **{"b": lambda: 1 / 0})
    assert isinstance(d, dict)


@pytest.mark.parametrize(
    "data, expected_foo, expected_bar, expected_errors",
    [
        (
            {"foo": lambda: 1, "bar": lambda: 1 / 0},
            1,
            None,
            {"bar": {"type": "ZeroDivisionError", "message": "division by zero"}},
        ),
        ({"foo": 1, "bar": lambda: 2}, 1, 2, {}),
    ],
)
def test_data_item_init(data, expected_foo, expected_bar, expected_errors):
    item = TestItem(**data)
    assert item.foo == expected_foo
    assert item.bar == expected_bar
    assert item.errors == expected_errors


def test_item_data_init_kwargs():
    item = TestItem(foo=lambda: 1, bar=lambda: 1 / 0)
    assert item.foo == 1
    assert item.bar is None
    assert item.errors == {
        "bar": {"type": "ZeroDivisionError", "message": "division by zero"}
    }
