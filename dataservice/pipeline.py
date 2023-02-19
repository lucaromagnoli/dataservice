import random
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, NewType

ResultsType = NewType("ResultsType", tuple)


class Pipeline:
    def __init__(self, data: ResultsType):
        self.data = data
        self.nodes = defaultdict(lambda: [])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.process()

    def add_node(self, func: Callable[[ResultsType, ...], None], parallel=True):
        if not self.nodes:
            key = 1
        else:
            last_node = list(self.nodes.keys())[-1]
            if parallel:
                key = last_node
            else:
                key = last_node + 1
        self.nodes[key].append(func)
        return self

    def process(self):
        for level, nodes in self.nodes.items():
            futures = []
            with ProcessPoolExecutor(max_workers=len(nodes)) as pool:
                for node in nodes:
                    futures.append(pool.submit(node, self.data))
            for future in futures:
                future.result()


def do_x(results):
    print("DO X")
    for result in results:
        time.sleep(random.randint(0, 200) / 100)
        print(f"Doing x on result {result}")


def do_y(results):
    print("DO Y")
    for result in results:
        time.sleep(random.randint(0, 200) / 100)
        print(f"Doing y on result {result}")


def do_z(results):
    print("DO Z")
    for result in results:
        time.sleep(random.randint(0, 200) / 100)
        print(f"Doing z on result {result}")


def do_w(results):
    print("DO W")
    for result in results:
        time.sleep(random.randint(0, 200) / 100)
        print(f"Doing w on result {result}")


results = list(f"Result {i}" for i in range(10))


if __name__ == "__main__":
    with Pipeline(results) as pipeline:
        pipeline.add_node(do_x).add_node(do_y).add_node(do_z, parallel=False).add_node(
            do_w
        )
