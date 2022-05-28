"""Base for Entities"""
import csv


class Base:
    """Base for Entities"""

    delimiter = ""
    encoding = "utf-8"

    def __init__(self, lunch_money, file_name):
        self.assets = []
        self.file_name = file_name
        self.lunch_money = lunch_money

    def read_rows(self, field_names):
        """Read lines from CSV files and return a list"""
        with open(self.file_name, encoding=self.encoding) as csvfile:
            if self.delimiter:
                reader = csv.DictReader(csvfile, field_names, delimiter=self.delimiter)
            else:
                reader = csv.DictReader(csvfile, field_names)
            return list(reader)

    def define_asset(self):
        """Define assets or accounr target in lunch money"""
