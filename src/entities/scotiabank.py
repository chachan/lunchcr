"""Scotiabank parser classes."""

import datetime
from pathlib import Path
from typing import ClassVar

import click
from lunchable import TransactionInsertObject
from lunchable.exceptions import LunchMoneyHTTPError
from lunchable.models import AssetsObject

from entities.base import Base
from utils import LunchMoneyCR, _float, _str, config_logger, slugify


class ScotiabankAccount(Base):
    """Parser for Credit Cards."""

    transaction_field_names: ClassVar = [
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
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list[AssetsObject]:
        """Tells if file_name is a valid Scotiabank account CSV file."""
        instance = ScotiabankAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self) -> None:
        """Define assets or account target in lunch money."""
        rows = self.read_rows(self.transaction_field_names)
        if not rows or not ScotiabankAccount.clean_transaction(rows[1]):
            self.assets = []
            return
        self.assets: list[AssetsObject] = [
            a for a in self.lunch_money.cached_assets if a.name == rows[1].get("NUMERO_CUENTA")
        ]

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        logger = config_logger("entities/scotiabank.py")
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

        logger.debug("Raw transactions: %d", len(rows))
        cleaned_transactions = list(filter(ScotiabankAccount.clean_transaction, rows))
        cleaned_transactions.sort(key=ScotiabankAccount._date)
        logger.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = ScotiabankAccount._date(cleaned_transactions[0])
        ends = ScotiabankAccount._date(cleaned_transactions[-1])
        logger.debug("from %s to %s", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            logger.info("Applied transactions: %d", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        logger = config_logger("entities/scotiabank.py")
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
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=ScotiabankAccount._debit_as_negative(transaction),
                skip_balance_update=False,
            )
            if result:
                logger.info("Applied transaction: %s-%s", result, self._external_id(transaction))
        except (ValueError, LunchMoneyHTTPError) as exception:
            logger.debug("Could not applied transaction: %s", transaction.get("CONCEPTO"))
            logger.debug(exception)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Ensure no exceptions are raised."""
        try:
            ScotiabankAccount._external_id(transaction)
        except (ValueError, TypeError):
            return {}
        return transaction

    @staticmethod
    def _reference(transaction: dict) -> str:
        return transaction["REFERENCIA"]

    @staticmethod
    def _date(transaction: dict) -> datetime.date:
        dt = datetime.datetime.strptime(transaction["FECHA"], "%d%m%Y").replace(tzinfo=datetime.UTC)
        return dt.date()

    @staticmethod
    def _notes(transaction: dict) -> str:
        return transaction["CONCEPTO"]

    @staticmethod
    def _amount(transaction: dict) -> float:
        return _float(transaction["MONTO"]) / 100

    @staticmethod
    def _debit_as_negative(transaction: dict) -> bool:
        return transaction["TIPO_MOVIMIENTO"] == "C"

    @staticmethod
    def _external_id(transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    ScotiabankAccount._reference(transaction),
                    ScotiabankAccount._date(transaction).isoformat(),
                    ScotiabankAccount._notes(transaction),
                    str(ScotiabankAccount._amount(transaction)),
                ],
            ),
        )


class ScotiabankCreditCard(Base):
    """Parse for credit cards."""

    asset_field_names: ClassVar = []
    delimiter = ","
    transaction_field_names: ClassVar = [
        "Número de Referencia",
        "Fecha de Movimiento",
        "Descripción",
        "Monto",
        "Moneda",
        "Tipo",
    ]

    @staticmethod
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list[AssetsObject]:
        """Tell if file_name is a valid Scotiabank credit card CSV file."""
        instance = ScotiabankCreditCard(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self) -> None:
        """Define assets or accounr target in lunch money."""
        rows = self.read_rows(self.transaction_field_names)
        if not rows:
            self.assets = []
            return
        try:
            ScotiabankCreditCard._date(rows[2])
        except (ValueError, TypeError, AttributeError, IndexError):
            self.assets = []
            return

        try:
            self.assets: list[AssetsObject] = []
            for row in rows:
                if row["Número de Referencia"] == "Tarjeta Número:":
                    self.assets.extend(
                        a for a in self.lunch_money.cached_assets if row["Fecha de Movimiento"][-4:] in a.name
                    )
        except TypeError:
            self.assets = []
            return

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        logger = config_logger("entities/scotiabank.py")
        if not self.assets:
            self.define_asset()

        if not getattr(self, "rows", []):
            self.rows = self.read_rows(self.transaction_field_names)

        cleaned_transactions = list(filter(ScotiabankCreditCard.clean_transaction, self.rows))
        cleaned_transactions.sort(key=ScotiabankCreditCard._date)
        logger.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = ScotiabankCreditCard._date(cleaned_transactions[0])
        ends = ScotiabankCreditCard._date(cleaned_transactions[-1])
        logger.debug("from %s to %s", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            logger.info("Applied transactions: %d", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        logger = config_logger("entities/scotiabank.py")
        try:
            _asset = self._asset(transaction)
            if not _asset:
                return []
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
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=ScotiabankCreditCard._debit_as_negative(transaction),
                skip_balance_update=False,
            )
            if result:
                logger.info("Applied transaction: %s-%s", result, self._external_id(transaction))
        except (ValueError, LunchMoneyHTTPError) as exception:
            logger.debug("Could not applied transaction: %s", transaction.get("Descripción"))
            logger.debug(exception)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Parse raw row and build TransactionInsertObject."""
        try:
            day, month, year = transaction["Fecha de Movimiento"].split("/")
            datetime.date(int(year), int(month), int(day))
        except ValueError:
            return {}
        return transaction

    @staticmethod
    def _date(transaction: dict) -> datetime.date:
        day, month, year = transaction["Fecha de Movimiento"].split("/")
        return datetime.date(int(year), int(month), int(day))

    def _asset(self, transaction: dict) -> AssetsObject | None:
        """Locate asset by looping backwards in row list from transaction location."""
        # locate reference position in rows list.
        position = -1
        for i, row in enumerate(self.rows):
            if row["Número de Referencia"] == transaction["Número de Referencia"]:
                position = i
                break

        # locate credit card number by looping backwards in rows list from above position.
        card_number = ""
        for row in self.rows[position:0:-1]:
            if row["Número de Referencia"] == "Tarjeta Número:":
                card_number = row["Fecha de Movimiento"][-4:]
                break

        # local credit card number in cached assets list
        for asset in self.assets:
            if card_number in asset.name and transaction["Moneda"].lower() == asset.currency:
                return asset

        return None

    @staticmethod
    def _amount(transaction: dict) -> float:
        return abs(_float(transaction["Monto"]))

    @staticmethod
    def _notes(transaction: dict) -> str:
        return transaction["Descripción"]

    def _external_id(self, transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    _str(transaction["Número de Referencia"]),
                    str(self._notes(transaction)),
                    str(self._amount(transaction)),
                ],
            ),
        )

    @staticmethod
    def _debit_as_negative(transaction: dict) -> bool:
        return transaction["Tipo"] == "CREDITO"
