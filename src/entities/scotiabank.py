"""Scotiabank parser classes"""
import datetime

import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import _float, _str, config_logger

LOGGER = config_logger("entities/scotiabank.py")


class ScotiabankAccount(Base):
    """Parser for Credit Cards"""

    transaction_field_names = [
        "TIPO_TRANSACCION",
        "TIPO_MOVIMIENTO",
        "MONEDA",
        "NUMERO_CUENTA",
        "REFERENCIA",
        "FECHA",
        "MONTO",
        "CONCEPTO",
    ]
    delimiter = ";"

    @staticmethod
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid Scotiabank account CSV file"""
        instance = ScotiabankAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self):
        """Define assets or account target in lunch money"""
        rows = self.read_rows(self.transaction_field_names)
        if not rows or not ScotiabankAccount.clean_transaction(rows[1]):
            self.assets = []
            return
        self.assets = [a for a in self.lunch_money.cached_assets if a.name == rows[1].get("NUMERO_CUENTA")]

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

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
            ScotiabankAccount._external_id(transaction)
            return transaction
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _reference(transaction):
        return transaction.get("REFERENCIA")

    @staticmethod
    def _date(transaction):
        dt = datetime.datetime.strptime(transaction.get("FECHA"), "%d%m%Y")
        return datetime.datetime.strftime(dt, "%Y-%m-%d")

    @staticmethod
    def _notes(transaction):
        return transaction.get("CONCEPTO")

    @staticmethod
    def _amount(transaction):
        return _float(transaction.get("MONTO")) / 100

    @staticmethod
    def _debit_as_negative(transaction):
        return transaction.get("TIPO_MOVIMIENTO") == "C"

    @staticmethod
    def _external_id(transaction):
        return slugify(
            " ".join(
                [
                    ScotiabankAccount._reference(transaction),
                    ScotiabankAccount._date(transaction),
                    ScotiabankAccount._notes(transaction),
                    str(ScotiabankAccount._amount(transaction)),
                ]
            )
        )


class ScotiabankCreditCard(Base):
    """Parser for Credit Cards"""

    asset_field_names = []
    delimiter = ","
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
            self.assets = []
            return
        try:
            ScotiabankCreditCard._date(rows[2])
        except (ValueError, TypeError):
            self.assets = []
            return

        try:
            _asset = rows[1]["Fecha de Movimiento"][-4:]  # row[1] is nonesense
        except TypeError:
            self.assets = []
            return
        by_name = lambda a: a.name[-4:] == _asset
        self.assets = list(filter(by_name, self.lunch_money.cached_assets))

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
