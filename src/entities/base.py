"""Base for Entities."""

import csv
from pathlib import Path

from utils import LunchMoneyCR, config_logger


class Base:
    """Base for Entities."""

    delimiter = ""
    encoding = "utf-8"

    def __init__(self, lunch_money: LunchMoneyCR, file_name: Path) -> None:
        """Initialize."""
        self.assets = []
        self.file_name = file_name
        self.lunch_money = lunch_money

    def read_rows(self, field_names: list) -> list[dict] | list:
        """Read lines from CSV files and return a list."""
        logger = config_logger("entities/base.py")
        with Path(self.file_name).open(encoding=self.encoding) as csvfile:
            if self.delimiter:
                reader = csv.DictReader(csvfile, field_names, delimiter=self.delimiter)
            else:
                reader = csv.DictReader(csvfile, field_names)
            try:
                rows = list(reader)
            except UnicodeDecodeError:
                logger.debug("%s - could not decode file using %s", self.__class__.__name__, self.encoding)
                return []
            return rows

    def define_asset(self) -> None:
        """Define assets or account target in lunch money."""
