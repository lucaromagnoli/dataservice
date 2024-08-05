from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Callable, Iterable, Iterator, TypeVar

Result = TypeVar("Result")
ResultsIterable = Iterable[Result]
ResultsTuple = tuple[Result, ...]
ResultsList = list[Result]


class Pipeline:
    def __init__(self, results: ResultsIterable):
        """Initialize the pipeline.
        `self.nodes` is a dictionary where the keys represent the level of the node in the pipeline
        and the values represent the node functions."""
        self._results = results
        self._nodes: defaultdict = defaultdict(lambda: [])

    def run(self):
        """Run the pipeline."""
        return self._run(self._results)

    def _run(self, results: ResultsIterable) -> ResultsTuple:
        """Run the pipeline. The pipeline is run in a top-down manner, starting from the first node.
        Nodes are executed sequentially, with each function passing its results to the next function,
        while leaf nodes are executed in parallel."""
        # non-leaf nodes
        results = tuple(results)
        results = self._run_nodes(results)
        # leaf nodes
        if -1 in self._nodes:
            funcs = self._nodes[-1]
            with ProcessPoolExecutor() as executor:
                for func in funcs:
                    executor.submit(func, results)
        return results

    def _run_nodes(self, results: ResultsTuple) -> ResultsTuple:
        """Run the non-leaf nodes in the pipeline on a separate thread."""

        def inner():
            nonlocal results
            for k, v in self._nodes.items():
                if k == -1:
                    continue
                (func,) = self._nodes[k]
                results = tuple(func(results))
            return results

        with ThreadPoolExecutor() as executor:
            return executor.submit(inner).result()

    def _get_last_node(self) -> int:
        """Get the index of the last node in the pipeline."""
        return list(self._nodes.keys())[-1]

    def add_step(
        self, *funcs: Callable[[ResultsTuple], ResultsIterable], final: bool = False
    ) -> Pipeline:
        """Add a node to the pipeline. Each node is a function that takes the results of the previous node as input."""
        if final:
            if -1 in self._nodes:
                raise ValueError("A final step has already been added.")
            key = -1
            self._nodes[key].extend(funcs)
            return self

        func = funcs[0]
        if not self._nodes:
            key = 1
        else:
            last_node = self._get_last_node()
            key = last_node + 1
        self._nodes[key].append(func)
        return self

    def group_by(self, key: Callable[[Result], str]) -> Iterator[tuple[str, Pipeline]]:
        """Group the results by the key."""
        for k, v in self._group_by(self._results, key).items():
            yield k, self.__class__(v)

    def _group_by(
        self, results: ResultsIterable, key: Callable[[Result], str]
    ) -> defaultdict[str, ResultsList]:
        """Group the results by the key."""
        results = tuple(results)
        groups = defaultdict(list)
        for result in results:
            k = key(result)
            groups[k].append(result)
        return groups
