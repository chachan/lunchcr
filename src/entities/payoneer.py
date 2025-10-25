"""Payoneer parser classes."""
import datetime
from typing import TYPE_CHECKING, ClassVar

import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import LunchMoneyCR, _float, _str, config_logger

if TYPE_CHECKING:
    from pathlib import Path

    from lunchable.models import AssetsObject

LOGGER = config_logger("entities/payoneer.py")


class PayoneerAccount(Base):
    """Parser for Bank Accounts."""

    transaction_field_names: ClassVar = [
        "Transaction Date",
        "Transaction Time",
        "Time Zone",
        "Transaction ID",
        "Description",
        "Credit Amount",
        "Debit Amount",
        "Currency",
        "Transfer Amount",
        "Transfer Amount Currency",
        "Status",
        "Additional Description",
        "Store Name",
        "Source",
        "Target",
        "Reference ID",
    ]

    @staticmethod
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list[AssetsObject]:
        """Tell if file_name is a valid Payoneer Account CSV file."""
        instance = PayoneerAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self) -> None:
        """Define assets or accounr target in lunch money."""
        rows = self.read_rows(self.transaction_field_names)
        if not rows:
            self.assets = []
            return
        try:
            int(rows[1].get("Transaction ID"))
        except (ValueError, TypeError):
            self.assets = []
            return
        self.assets = [a for a in self.lunch_money.cached_assets if a.name == "PAYONEER"]

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(PayoneerAccount.transaction_field_names)

        raw_transactions = rows[1:]
        LOGGER.debug("Raw transactions detected: %d", len(raw_transactions))
        cleaned_transactions = list(filter(PayoneerAccount.clean_transaction, raw_transactions))
        cleaned_transactions.reverse()
        LOGGER.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = PayoneerAccount._date(cleaned_transactions[0])
        ends = PayoneerAccount._date(cleaned_transactions[-1])
        LOGGER.debug("from %d to %d", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            LOGGER.info("Applied transactions: %s", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        try:
            _asset = self.assets[0]
            transaction_insert = TransactionInsertObject(
                amount=_float(PayoneerAccount._amount(transaction).replace(",", "")),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=PayoneerAccount._date(transaction),
                external_id=PayoneerAccount._external_id(transaction),
                notes=PayoneerAccount._notes(transaction),
                payee="",
            )
            _debit_as_negative = PayoneerAccount._debit_as_negative(transaction)
            result = self.lunch_money.insert_transactions(
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=_debit_as_negative,
                skip_balance_update=False,
            )
            if result:
                LOGGER.info("Applied transaction: %s-%s", result, PayoneerAccount._external_id(transaction))
        except ValueError:
            LOGGER.exception("could not applied transaction: %s", transaction)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Parse raw row and build TransactionInsertObject."""
        return transaction

    @staticmethod
    def _amount(transaction: dict) -> str:
        return transaction["Credit Amount"] or transaction["Debit Amount"]

    @staticmethod
    def _date(transaction: dict) -> datetime.date:
        month, day, year = _str(transaction["Transaction Date"]).split("/")
        return datetime.date(int(year), int(month), int(day))

    @staticmethod
    def _external_id(transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    _str(transaction["Transaction ID"]),
                    PayoneerAccount._notes(transaction),
                    _str(PayoneerAccount._amount(transaction)),
                ],
            ),
        )

    @staticmethod
    def _notes(transaction: dict) -> str:
        return transaction["Description"]

    @staticmethod
    def _debit_as_negative(transaction: dict) -> bool:
        return bool(transaction["Credit Amount"])
