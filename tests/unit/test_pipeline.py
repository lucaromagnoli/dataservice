import json
import os
from collections import defaultdict
from dataclasses import dataclass

import pytest

from dataservice.pipeline import Pipeline


@pytest.fixture
def pipeline(request):
    return Pipeline(request.param)


@pytest.fixture
def file_to_write(request):
    name = request.config.rootdir.join("test_file.json")
    yield name
    if os.path.isfile(name):
        os.remove(name)


def double_key(iterable):
    """Double the value of the key in the dictionary."""
    for x in iterable:
        x["key"] *= 2
    return iterable


def write_to_file(results: list[dict], file_name):
    with open(file_name, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results written to {file_name}")


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_add_step(pipeline):
    pipeline.add_step(double_key)
    results = pipeline.run()
    assert results == ({"key": 2}, {"key": 4}, {"key": 6})


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_add_multiple_steps(pipeline):
    results = (
        pipeline.add_step(double_key).add_step(double_key).add_step(double_key).run()
    )
    assert results == ({"key": 8}, {"key": 16}, {"key": 24})


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_add_final_step_no_previous_node(pipeline):
    """Test adding a final step to the pipeline. Input results are not modified by the last step."""
    results = pipeline.add_final_step([double_key]).run()
    assert results == ({"key": 1}, {"key": 2}, {"key": 3})


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_add_final_step_with_previous_nodes(pipeline):
    """Test adding a final step to the pipeline. Input results are not modified by the last step."""
    results = (
        pipeline.add_step(double_key)
        .add_step(double_key)
        .add_step(double_key)
        .add_final_step([double_key])
        .run()
    )
    assert results == ({"key": 8}, {"key": 16}, {"key": 24})


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_add_final_step_raises_error(pipeline):
    """Test adding a final step to the pipeline raises an error if a final step has already been added."""

    with pytest.raises(ValueError):
        pipeline.add_step(double_key).add_step(double_key).add_step(
            double_key
        ).add_final_step([double_key]).add_final_step([double_key])


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_run_threaded(pipeline, mocker):
    """Test running the pipeline with a threaded executor."""

    def return_value():
        pass

    return_value.result = lambda: ({"key": 2}, {"key": 4}, {"key": 6})
    mocked_thread_pool = mocker.patch(
        "dataservice.pipeline.ThreadPoolExecutor.submit", return_value=return_value
    )
    results = pipeline.add_step(double_key).run()
    assert results == ({"key": 2}, {"key": 4}, {"key": 6})
    mocked_thread_pool.assert_called_once()


@pytest.mark.parametrize(
    "pipeline",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),
    ],
    indirect=True,
)
def test_pipeline_leaves_runs_in_processpool(pipeline, mocker):
    """Test running the pipeline with a threaded executor."""

    mocked_process_pool = mocker.patch(
        "dataservice.pipeline.ProcessPoolExecutor.submit",
    )
    pipeline.add_final_step([double_key, double_key]).run()
    assert len(mocked_process_pool.call_args_list) == 2


@dataclass
class FooResult:
    foo: str


@dataclass
class BarResult:
    bar: str


@pytest.mark.parametrize(
    "results, key_func, expected",
    [
        pytest.param(
            [{"key": i} for i in range(1, 11)],
            lambda x: "odd_" if x["key"] % 2 else "even",
            defaultdict(
                int,
                {
                    "even": [
                        {"key": 2},
                        {"key": 4},
                        {"key": 6},
                        {"key": 8},
                        {"key": 10},
                    ],
                    "odd_": [
                        {"key": 1},
                        {"key": 3},
                        {"key": 5},
                        {"key": 7},
                        {"key": 9},
                    ],
                },
            ),
            id="list",
        ),
        pytest.param(
            [
                *[FooResult(foo=str(i)) for i in range(1, 11)],
                *[BarResult(bar=str(i)) for i in range(1, 11)],
            ],
            lambda x: f"{x.__class__.__name__}s",
            defaultdict(
                int,
                {
                    "FooResults": [FooResult(foo=str(i)) for i in range(1, 11)],
                    "BarResults": [BarResult(bar=str(i)) for i in range(1, 11)],
                },
            ),
            id="list",
        ),
    ],
)
def test__group_by(results, key_func, expected):
    pipeline = Pipeline(results)
    groups = pipeline._group_by(results, key_func)
    assert groups == expected


@pytest.mark.parametrize(
    "results, key_func, expected",
    [
        pytest.param(
            [{"key": i} for i in range(1, 11)],
            lambda x: "odd_" if x["key"] % 2 else "even",
            {
                "even": (
                    {"key": 2},
                    {"key": 4},
                    {"key": 6},
                    {"key": 8},
                    {"key": 10},
                ),
                "odd_": (
                    {"key": 1},
                    {"key": 3},
                    {"key": 5},
                    {"key": 7},
                    {"key": 9},
                ),
            },
            id="list",
        ),
        pytest.param(
            [
                *[FooResult(foo=str(i)) for i in range(1, 11)],
                *[BarResult(bar=str(i)) for i in range(1, 11)],
            ],
            lambda x: f"{x.__class__.__name__}s",
            {
                "FooResults": tuple(FooResult(foo=str(i)) for i in range(1, 11)),
                "BarResults": tuple(BarResult(bar=str(i)) for i in range(1, 11)),
            },
            id="list",
        ),
    ],
)
def test_group_by(results, key_func, expected):
    pipeline = Pipeline(results)
    groups = {}
    for group_name, group in pipeline.group_by(key_func):
        groups[group_name] = group.run()
    assert groups == expected


def test_write_to_file(file_to_write):
    results = [{"key": 1}, {"key": 2}, {"key": 3}]
    write_to_file(results, file_to_write)
    assert os.path.isfile(file_to_write)
    with open(file_to_write) as f:
        assert json.load(f) == results
