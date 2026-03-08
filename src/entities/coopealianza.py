"""Coopealianza parser classes."""

import datetime
from pathlib import Path
from typing import ClassVar

import click
from lunchable import TransactionInsertObject
from lunchable.exceptions import LunchMoneyHTTPError
from lunchable.models import AssetsObject

from entities.base import Base
from utils import LunchMoneyCR, _float, _str, config_logger, slugify


class CoopealianzaAccount(Base):
    """Parser for Coopealianza accounts."""

    encoding = "utf-16le"

    asset_field_names: ClassVar = [
        "Titular",
        "Cuenta #",
        "Alias",
        "Fecha del reporte",
        "Sucursal",
        "Oficial de cuenta",
        "Saldo",
    ]

    transaction_field_names: ClassVar = [
        "Fecha",
        "Descripción",
        "Débito",
        "Crédito",
        "Saldo",
    ]

    @staticmethod
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list[AssetsObject]:
        """Tells if file_name is a valid Coopealianza account CSV file."""
        instance = CoopealianzaAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self) -> None:
        """Define assets or account target in lunch money."""
        rows = self.read_rows(CoopealianzaAccount.asset_field_names)
        if not rows:
            self.assets = []
            return
        product = _str(rows[1].get("Cuenta #", ""))
        self.assets = list(filter(lambda a: a.name == product, self.lunch_money.cached_assets))

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        logger = config_logger("entities/coopealianza.py")
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

        logger.debug("Raw transactions: %d", len(rows))
        cleaned_transactions = list(filter(CoopealianzaAccount.clean_transaction, rows[5:]))
        cleaned_transactions.sort(key=CoopealianzaAccount._date)
        logger.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = CoopealianzaAccount._date(cleaned_transactions[0])
        ends = CoopealianzaAccount._date(cleaned_transactions[-1])
        logger.debug("from %s to %s", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            logger.info("Applied transactions: %d", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        logger = config_logger("entities/coopealianza.py")
        try:
            _asset = self.assets[0]
            transaction_insert = TransactionInsertObject(
                amount=CoopealianzaAccount._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=self._date(transaction),
                external_id=self._external_id(transaction),
                notes=CoopealianzaAccount._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=CoopealianzaAccount._debit_as_negative(transaction),
                skip_balance_update=False,
            )
            if result:
                logger.info("Applied transaction: %s-%s", result, self._external_id(transaction))
        except (ValueError, LunchMoneyHTTPError, IndexError) as exception:
            logger.debug("Could not applied transaction: %s", transaction.get("Descripción"))
            logger.debug(exception)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Ensure no exceptions are raised."""
        try:
            CoopealianzaAccount._external_id(transaction)
        except (ValueError, TypeError):
            return {}
        return transaction

    @staticmethod
    def _amount(transaction: dict) -> float:
        if transaction["Débito"]:
            return _float(transaction["Débito"].replace("\xa0", "").replace(" ", "").replace(",", "."))
        return _float(transaction["Crédito"].replace("\xa0", "").replace(" ", "").replace(",", "."))

    @staticmethod
    def _date(transaction: dict) -> datetime.date:
        dt = datetime.datetime.strptime(transaction["Fecha"], "%d/%m/%Y").replace(tzinfo=datetime.UTC)
        return dt.date()

    @staticmethod
    def _external_id(transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    transaction["Fecha"],
                    transaction["Descripción"],
                    transaction["Débito"],
                    transaction["Crédito"],
                    transaction["Saldo"],
                ],
            ),
        )

    @staticmethod
    def _notes(transaction: dict) -> str:
        return transaction["Descripción"]

    @staticmethod
    def _debit_as_negative(transaction: dict) -> bool:
        return bool(transaction["Crédito"])
