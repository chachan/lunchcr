import csv


class Base:
    def read_rows(self, field_names):
        with open(self.file_name, encoding="cp1252") as csvfile:
            reader = csv.DictReader(csvfile, field_names)
            return list(reader)
