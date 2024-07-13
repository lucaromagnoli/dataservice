import random
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, NewType, Iterable

ResultsType = NewType("ResultsType", tuple)


class Pipeline:
    def __init__(self):
        self.nodes = defaultdict(lambda: [])

    def __call__(self, results: ResultsType = None):
        return self.run(results)

    def add_node(self, func: Callable[[ResultsType, ...], None]):
        if not self.nodes:
            key = 1
        else:
            last_node = list(self.nodes.keys())[-1]
            key = last_node + 1
        self.nodes[key].append(func)
        return self

    def add_nodes(self, funcs: Iterable[Callable[[ResultsType, ...], None]]):
        if not self.nodes:
            key = 1
        else:
            last_node = list(self.nodes.keys())[-1]
            key = last_node + 1
        self.nodes[key].extend(funcs)
        return self

    def run(self, results: ResultsType = None):
        for level, node_funcs in self.nodes.items():
            if len(node_funcs) == 1:
                with ProcessPoolExecutor(max_workers=1) as pool:
                    for node_func in node_funcs:
                        task = pool.submit(node_func, results)
                        results = task.result()
            else:
                with ProcessPoolExecutor(max_workers=len(node_funcs)) as pool:
                    tasks = [
                        pool.submit(node_func, results) for node_func in node_funcs
                    ]
                    results = [task.result() for task in tasks]
        return results

