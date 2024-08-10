"""Simple file writers implementation."""

import csv
import json
import logging
from pathlib import Path
from typing import Iterable

from dataservice.data import BaseDataItem, DataSink

logger = logging.getLogger(__name__)


class FileWriter(DataSink):
    """Base class for file writers."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def get_data_dicts(self, data: Iterable[dict | BaseDataItem]) -> list[dict]:
        """Yield data dictionaries from the data items.

        :param data: An iterable of data items.
        :return: A list of dictionaries.
        """
        for datum in data:
            if isinstance(datum, BaseDataItem):
                yield datum.model_dump()
            else:
                yield datum


class CSVWriter(FileWriter):
    """Writes data to a CSV file."""

    def write(self, data: Iterable[dict | BaseDataItem]):
        """Write data to a CSV file.

        :param data: An iterable of data items.
        """
        data = list(self.get_data_dicts(data))
        with open(self.file_path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Data written to {self.file_path}")


class JsonWriter(FileWriter):
    """Writes data to a JSON file."""

    def write(self, data: Iterable[dict | BaseDataItem]):
        """Write data to a JSON file.

        :param data: An iterable of data items.
        """
        data = list(self.get_data_dicts(data))
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Data written to {self.file_path}")


writers = {
    "csv": CSVWriter,
    "json": JsonWriter,
}
