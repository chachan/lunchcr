"""Base for Entities"""
import csv


class Base:
    """Base for Entities"""

    def __init__(self, lunch_money, file_name):
        self.lunch_money = lunch_money
        self.file_name = file_name
        self.assets = []

    def read_rows(self, field_names, encoding):
        """Read lines from CSV files and return a list"""
        with open(self.file_name, encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile, field_names)
            return list(reader)

    def define_asset(self):
        """Define assets or accounr target in lunch money"""
