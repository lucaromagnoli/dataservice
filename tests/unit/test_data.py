from dataservice.data import DataWrapper


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
    assert d.a == 1
    assert d.b is None
    assert d.exceptions == {
        "b": {"type": "ZeroDivisionError", "message": "division by zero"}
    }


def test_datawrapper_init_dict():
    d = DataWrapper(**{"a": lambda: 1, "b": lambda: 1 / 0})
    assert d.a == 1
    assert d.b is None
    assert d.exceptions == {
        "b": {"type": "ZeroDivisionError", "message": "division by zero"}
    }


def test_datawrapper_is_instance_of_dict():
    d = DataWrapper(a=lambda: 1, **{"b": lambda: 1 / 0})
    assert isinstance(d, dict)
