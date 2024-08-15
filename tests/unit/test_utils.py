from functools import partial

from dataservice._utils import _get_func_name


def test_get_func_name_for_regular_function():
    def sample_function():
        pass

    assert _get_func_name(sample_function) == "sample_function"


def test_get_func_name_for_partial_function():
    def sample_function():
        pass

    partial_func = partial(sample_function)
    assert _get_func_name(partial_func) == "sample_function"


def test_get_func_name_for_partial_with_wrapped_function():
    def sample_function():
        pass

    partial_func = partial(sample_function, wrapped=sample_function)
    assert _get_func_name(partial_func) == "sample_function"


def test_get_func_name_for_lambda_function():
    lambda_func = lambda x: x  # noqa
    assert _get_func_name(lambda_func) == "<lambda>"


def test_get_func_name_for_class_instance():
    class SampleClass:
        pass

    instance = SampleClass()
    assert _get_func_name(instance) == "SampleClass"


def test_get_func_name_for_callable_instance():
    class CallableClass:
        def __call__(self):
            pass

    instance = CallableClass()
    assert _get_func_name(instance) == "CallableClass"
