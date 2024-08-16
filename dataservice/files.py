"""Simple file writers implementation."""

import csv
import json
import logging
from pathlib import Path
from typing import Iterable, Iterator

from pydantic import BaseModel

from dataservice.data import DataSink

logger = logging.getLogger(__name__)


class FileWriter(DataSink):
    """Base class for file writers."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def get_data_dicts(self, results: Iterable[dict | BaseModel]) -> Iterator[dict]:
        """Yield data dictionaries from the data items.

        :param results: An iterable of result items.
        :return: A list of dictionaries.
        """
        for result in results:
            if isinstance(result, BaseModel):
                exclude = set()
                if hasattr(result, "errors"):
                    exclude = {"errors"}
                yield result.model_dump(exclude=exclude)
            else:
                yield result


class CSVWriter(FileWriter):
    """Writes data to a CSV file."""

    def write(self, results: Iterable[dict | BaseModel]):
        """Write data to a CSV file.

        :param results_dicts: An iterable of data items.
        """
        results_dicts: list[dict] = list(self.get_data_dicts(results))
        with open(self.file_path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=results_dicts[0].keys())
            writer.writeheader()
            writer.writerows(results_dicts)
        logger.info(f"Data written to {self.file_path}")


class JsonWriter(FileWriter):
    """Writes data to a JSON file."""

    def write(self, results: Iterable[dict | BaseModel]):
        """Write data to a JSON file.

        :param results: An iterable of data items.
        """
        results = list(self.get_data_dicts(results))
        with open(self.file_path, "w") as f:
            json.dump(results, f, indent=4)
        logger.info(f"Data written to {self.file_path}")


writers = {
    "csv": CSVWriter,
    "json": JsonWriter,
}
