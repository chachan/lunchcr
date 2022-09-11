"""Scotiabank parser classes"""
import csv
import datetime

import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import _float, _str, config_logger

LOGGER = config_logger("entities/scotiabank.py")


class ScotiabankAccount(Base):
    """Parser for Credit Cards"""

    asset_field_names = []
    delimiter = ","

    @staticmethod
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid Scotiabank account CSV file"""
        instance = ScotiabankAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def read_rows(self):
        with open(self.file_name, encoding=self.encoding) as csv_file:
            reader = csv.reader(csv_file, delimiter=self.delimiter)
            try:
                rows = list(reader)[1:]
                return rows
            except UnicodeDecodeError:
                LOGGER.debug(f"could not decode file using {self.encoding}")
                return []

    def define_asset(self):
        """Define assets or account target in lunch money"""
        rows = self.read_rows()
        if not rows or not ScotiabankAccount.clean_transaction(rows[0]):
            return []
        self.assets = [
            a for a in self.lunch_money.cached_assets if a.name == "CR79012300120123397016"
        ]  # CUENTA UNIVERSAL USD

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows()

        LOGGER.debug(f"Raw transactions: {len(rows)}")
        cleaned_transactions = list(filter(ScotiabankAccount.clean_transaction, rows))
        cleaned_transactions.sort(key=ScotiabankAccount._date)
        LOGGER.debug(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = ScotiabankAccount._date(cleaned_transactions[0])
        ends = ScotiabankAccount._date(cleaned_transactions[-1])
        LOGGER.debug(f"from {starts} to {ends}")
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            LOGGER.info(f"Applied transactions: {applied_transactions}")

    def insert_transaction(self, transaction):
        """Actual single insert"""
        try:
            _asset = self.assets[0]
            transaction_insert = TransactionInsertObject(
                amount=ScotiabankAccount._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=ScotiabankAccount._date(transaction),
                external_id=self._external_id(transaction),
                notes=ScotiabankAccount._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                debit_as_negative=ScotiabankAccount._debit_as_negative(transaction),
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction_insert,
            )
            if result:
                LOGGER.info(f"Applied transaction: {result}-{self._external_id(transaction)}")
            return result
        except ValueError as exception:
            LOGGER.error(f"could not applied transaction: {transaction}")
            LOGGER.error(exception)
            return None

    @staticmethod
    def clean_transaction(transaction):
        """Ensure no exceptions are raised"""
        try:
            ScotiabankAccount._date(transaction)
            ScotiabankAccount._notes(transaction)
            ScotiabankAccount._amount(transaction)
            ScotiabankAccount._balance(transaction)
            if transaction[5] != "Débito" and transaction[5] != "Crédito":  # Crédito/Débito
                raise TypeError
            return transaction
        except (TypeError, KeyError):
            return None

    @staticmethod
    def _date(transaction):
        day, month, year = transaction[1].split("/")  # Fecha de Movimiento
        return f"{year}-{month}-{day}"

    @staticmethod
    def _amount(transaction):
        return _float(transaction[3].replace(",", ""))

    @staticmethod
    def _notes(transaction):
        return transaction[2]  # Descripción

    def _external_id(self, transaction):
        return slugify(
            " ".join(
                [
                    transaction[0],  # Número de Referencia
                    ScotiabankAccount._date(transaction),
                    ScotiabankAccount._notes(transaction),
                    str(ScotiabankAccount._balance(transaction)),
                ]
            )
        )

    @staticmethod
    def _balance(transaction):
        return _float(transaction[4].replace(",", ""))  # Balance?

    @staticmethod
    def _debit_as_negative(transaction):
        return transaction[5] == "Crédito"


class ScotiabankCreditCard(Base):
    """Parser for Credit Cards"""

    asset_field_names = []
    delimiter = ";"
    transaction_field_names = [
        "Número de Referencia",
        "Fecha de Movimiento",
        "Descripción",
        "Monto",
        "Moneda",
        "Tipo",
    ]

    @staticmethod
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid Scotiabank credit card CSV file"""
        instance = ScotiabankCreditCard(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self):
        """Define assets or accounr target in lunch money"""
        rows = self.read_rows(self.transaction_field_names)
        if not rows:
            return []
        try:
            _asset = rows[1]["Fecha de Movimiento"][-4:]
        except TypeError:
            return []
        by_name = lambda a: a.name[-4:] == _asset
        self.assets = list(filter(by_name, self.lunch_money.cached_assets))
        try:
            day, month, year = rows[2]["Fecha de Movimiento"].split("/")
            datetime.date(int(year), int(month), int(day))
        except (ValueError, TypeError):
            return []
        return self.assets

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

        cleaned_transactions = list(filter(ScotiabankCreditCard.clean_transaction, rows))
        cleaned_transactions.sort(key=ScotiabankCreditCard._date)
        LOGGER.debug(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = ScotiabankCreditCard._date(cleaned_transactions[0])
        ends = ScotiabankCreditCard._date(cleaned_transactions[-1])
        LOGGER.debug(f"from {starts} to {ends}")
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            LOGGER.info(f"Applied transactions: {applied_transactions}")

    def insert_transaction(self, transaction):
        """Actual single insert"""
        try:
            _asset = self._asset(transaction)
            transaction_insert = TransactionInsertObject(
                amount=ScotiabankCreditCard._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=self._date(transaction),
                external_id=self._external_id(transaction),
                notes=ScotiabankCreditCard._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                debit_as_negative=ScotiabankCreditCard._debit_as_negative(transaction),
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction_insert,
            )
            if result:
                LOGGER.info(f"Applied transaction: {result}-{self._external_id(transaction)}")
            return result
        except ValueError as exception:
            LOGGER.error(f"could not applied transaction: {transaction}")
            LOGGER.error(exception)
            return None

    @staticmethod
    def clean_transaction(transaction):
        """Parse raw row and build TransactionInsertObject"""
        try:
            day, month, year = transaction["Fecha de Movimiento"].split("/")
            datetime.date(int(year), int(month), int(day))
            return transaction
        except ValueError:
            return None

    @staticmethod
    def _date(transaction):
        day, month, year = transaction["Fecha de Movimiento"].split("/")
        return f"{year}-{month}-{day}"

    def _asset(self, transaction):
        crc = transaction["Moneda"].lower() == "crc"
        usd = transaction["Moneda"].lower() == "usd"
        if crc:
            return [a for a in self.assets if a.currency == "crc"][0]
        if usd:
            return [a for a in self.assets if a.currency == "usd"][0]
        return None

    @staticmethod
    def _amount(transaction):
        return _float(transaction["Monto"])

    @staticmethod
    def _notes(transaction):
        return transaction["Descripción"]

    def _external_id(self, transaction):

        return slugify(
            " ".join(
                [
                    _str(transaction["Número de Referencia"]),
                    str(self._notes(transaction)),
                    str(self._amount(transaction)),
                ]
            )
        )

    @staticmethod
    def _debit_as_negative(transaction):
        return transaction["Tipo"] == "CREDITO"
