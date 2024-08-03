import functools
import json
import os
from pathlib import Path
from unittest.mock import call

import pytest

from dataservice.pipeline import Pipeline


@pytest.fixture
def pipeline():
    return Pipeline()


@pytest.fixture
def file_to_write():
    name = Path.cwd() / "test_file.json"
    yield name


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
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_add_step(pipeline, results):
    pipeline.add_step(double_key)
    results = pipeline.run(results)
    assert results == ({"key": 2}, {"key": 4}, {"key": 6})


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_add_multiple_steps(pipeline, results):
    pipeline.add_step(double_key).add_step(double_key).add_step(double_key)
    results = pipeline.run(results)
    assert results == ({"key": 8}, {"key": 16}, {"key": 24})


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_add_final_step_no_previous_node(pipeline, results):
    """Test adding a final step to the pipeline. Input results are not modified by the last step."""
    pipeline.add_final_step([double_key])
    results = pipeline.run(results)
    assert results == ({"key": 1}, {"key": 2}, {"key": 3})


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_add_final_step_with_previous_nodes(pipeline, results):
    """Test adding a final step to the pipeline. Input results are not modified by the last step."""
    pipeline.add_step(double_key).add_step(double_key).add_step(
        double_key
    ).add_final_step([double_key])
    results = pipeline.run(results)
    assert results == ({"key": 8}, {"key": 16}, {"key": 24})


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_add_final_step_raises_error(pipeline, results):
    """Test adding a final step to the pipeline raises an error if a final step has already been added."""
    pipeline.add_step(double_key).add_step(double_key).add_step(
        double_key
    ).add_final_step([double_key])
    with pytest.raises(ValueError):
        pipeline.add_final_step([double_key])


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_run_threaded(pipeline, mocker, results):
    """Test running the pipeline with a threaded executor."""

    def return_value():
        pass

    return_value.result = lambda: ({"key": 2}, {"key": 4}, {"key": 6})
    mocked_thread_pool = mocker.patch(
        "dataservice.pipeline.ThreadPoolExecutor.submit", return_value=return_value
    )
    pipeline.add_step(double_key)
    results = pipeline.run(results)
    assert results == ({"key": 2}, {"key": 4}, {"key": 6})
    mocked_thread_pool.assert_called_once()


@pytest.mark.parametrize(
    "results",
    [
        [{"key": 1}, {"key": 2}, {"key": 3}],
        ({"key": 1}, {"key": 2}, {"key": 3}),
        iter([{"key": 1}, {"key": 2}, {"key": 3}]),

    ]
)
def test_pipeline_leaves_runs_in_processpool(pipeline, mocker, results):
    """Test running the pipeline with a threaded executor."""

    mocked_process_pool = mocker.patch(
        "dataservice.pipeline.ProcessPoolExecutor.submit",
    )
    pipeline.add_final_step([double_key, double_key])
    pipeline.run(results)
    assert len(mocked_process_pool.call_args_list) == 2


# def run_pipeline(mocker, pipeline):
#     mock_executor = mocker.patch("dataservice.pipeline.ProcessPoolExecutor")
#     mock_executor.return_value.__enter__.return_value.map = mocker.MagicMock()
#     with pipeline:
#         pass
#     return mock_executor
#
#
# def test_runs_pipeline_correctly(mocker, pipeline):
#     pipeline.add_step(pipeline_node_func)
#     pipeline.add_final_step([pipeline_leaf_func])
#     mock_executor = run_pipeline(mocker, pipeline)
#     mock_executor.return_value.__enter__.return_value.map.assert_called_once()
#
#
# def test_handles_empty_results(mocker):
#     pipeline = Pipeline([])
#     pipeline.add_step(pipeline_node_func)
#     pipeline.add_final_step([pipeline_leaf_func])
#     mock_executor = run_pipeline(mocker, pipeline)
#     mock_executor.return_value.__enter__.return_value.map.assert_not_called()
#
#
# def test_raises_error_on_multiple_leaves(pipeline):
#     pipeline.add_step(pipeline_node_func)
#     pipeline.add_final_step([pipeline_leaf_func])
#     with pytest.raises(ValueError):
#         pipeline.add_final_step([pipeline_leaf_func])
#
#
# def test_handles_no_nodes(mocker, pipeline):
#     pipeline.add_final_step([pipeline_leaf_func])
#     mock_executor = run_pipeline(mocker, pipeline)
#     mock_executor.return_value.__enter__.return_value.map.assert_called_once()
#
#
# def test_pipeline_add_node():
#     results = [1, 2, 3]
#     pipeline = Pipeline(results)
#     pipeline.add_step(lambda iterable: [x * 2 for x in iterable])
#     results = pipeline.run()
#     assert results == [2, 4, 6]
#
#
# def test_pipeline_context_manager(file_to_write):
#     results = [1, 2, 3]
#     write_func = functools.partial(write_to_file, file_name=file_to_write)
#     with Pipeline(results) as pipeline:
#         pipeline.add_step(lambda iterable: [x * 2 for x in iterable])
#         pipeline.add_final_step([write_func])
#         assert os.path.exists(file_to_write)
