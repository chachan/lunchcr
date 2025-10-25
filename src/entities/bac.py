"""BAC parser classes."""

import datetime
from pathlib import Path
from typing import ClassVar

import click
from lunchable import TransactionInsertObject
from lunchable.exceptions import LunchMoneyHTTPError
from lunchable.models import AssetsObject

from entities.base import Base
from utils import LunchMoneyCR, _float, _str, config_logger, slugify


class BACAccount(Base):
    """Parser for Bank Accounts."""

    asset_field_names: ClassVar = [
        "Number of customers",
        "Name",
        "Product",
        "Currency",
        "Initial balance",
        "Total balance",
        "Withheld and deferred funds",
        "Balance",
        "Date",
        "STBGAV",
        "STBUNC",
        "Message 1",
        "Message 2",
        "Message 3",
        "Message 4",
        "Message 5",
        "Message 6",
    ]
    encoding = "cp1252"
    transaction_field_names: ClassVar = [
        "Transaction date",
        "Transaction reference",
        "Transaction codes",
        "Description of transactions",
        "Transaction debit",
        "Transaction credit",
        "Transaction balance",
    ]

    @staticmethod
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list:
        """Tells if file_name is a valid BAC Account CSV file."""
        instance = BACAccount(lunch_money, file_name)
        instance.define_assets()
        return instance.assets

    def define_assets(self) -> None:
        """Define assets or account target in lunch money."""
        rows = self.read_rows(BACAccount.asset_field_names)
        if not rows:
            self.assets = []
            return
        product = _str(rows[1].get("Product", ""))
        self.assets = list(filter(lambda a: a.name == product, self.lunch_money.cached_assets))

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        logger = config_logger("entities/bac.py")
        if not self.assets:
            self.define_assets()

        rows = self.read_rows(self.transaction_field_names)

        raw_transactions = rows[4:]
        logger.debug("Raw transactions detected: %d", len(raw_transactions))
        cleaned_transactions = list(filter(BACAccount.clean_transaction, raw_transactions))
        if not cleaned_transactions:
            logger.warning("No transactions to apply")
            return
        logger.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = "-".join(BACAccount._date(cleaned_transactions[0]))
        ends = "-".join(BACAccount._date(cleaned_transactions[-1]))
        logger.debug("from %s to %s (DD/MM/YYYY)", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            logger.info("Applied transactions: %d", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        logger = config_logger("entities/bac.py")
        try:
            day, month, year = BACAccount._date(transaction)
            debit_as_negative = BACAccount._credit(transaction) > 0
            external_id = BACAccount._external_id(transaction)
            _asset = self.assets[0]
            transaction_insert = TransactionInsertObject(
                amount=BACAccount._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=datetime.date(int(year), int(month), int(day)),
                external_id=external_id,
                notes=BACAccount._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=debit_as_negative,
                skip_balance_update=False,
            )
            if result:
                logger.info("Applied transaction: %s-%s", result, external_id)
        except (ValueError, LunchMoneyHTTPError) as exception:
            logger.debug("Could not applied transaction: %s", transaction.get("Description of transactions", ""))
            logger.debug(exception)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Parse raw row and build TransactionInsertObject."""
        return transaction if BACAccount._balance(transaction) else {}

    @staticmethod
    def _external_id(transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    _str(transaction["Transaction reference"]),
                    BACAccount._balance(transaction),
                    BACAccount._notes(transaction),
                    str(BACAccount._amount(transaction)),
                ],
            ),
        )

    @staticmethod
    def _balance(transaction: dict) -> str:
        return transaction["Transaction balance"]

    @staticmethod
    def _notes(transaction: dict) -> str:
        return _str(transaction["Description of transactions"])

    @staticmethod
    def _credit(transaction: dict) -> float:
        return _float(transaction["Transaction credit"])

    @staticmethod
    def _amount(transaction: dict) -> float:
        debit = _float(transaction["Transaction debit"])
        credit = BACAccount._credit(transaction)
        return debit or credit

    @staticmethod
    def _date(transaction: dict) -> list:
        return _str(transaction["Transaction date"]).split("/")


class BACCreditCard(Base):
    """Parser for Credit Cards."""

    asset_field_names: ClassVar = [
        "Pro000000000000duct",
        "Name",
        "Date",
        "Minimum payment/due date",
        "Minimum payment/ Local Amount",
        "Minimum Payment / Dollars Amount",
        "Cash payment/Due date",
        "Cash payment / Local amount",
        "Cash payment / Dollar amount",
    ]
    encoding = "cp1252"
    transaction_field_names: ClassVar = ["Date", "", "Local", "Dollars "]

    @staticmethod
    def infer(lunch_money: LunchMoneyCR, file_name: Path) -> list:
        """Tells if file_name is a valid BAC credit card CSV file."""
        instance = BACCreditCard(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self) -> None:
        """Define assets or accounr target in lunch money."""
        rows = self.read_rows(BACCreditCard.asset_field_names)
        if not rows:
            self.assets = []
            return
        product = _str(rows[1]["Pro000000000000duct"])
        self.assets: list[AssetsObject] = list(filter(lambda a: a.name == product, self.lunch_money.cached_assets))

    def insert_transactions(self) -> None:
        """Insert transactions into an already define lunch money assets."""
        logger = config_logger("entities/bac.py")
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

        cleaned_transactions = list(filter(BACCreditCard.clean_transaction, rows))
        cleaned_transactions.sort(key=BACCreditCard._date)
        logger.debug("Cleaned transactions: %d", len(cleaned_transactions))
        starts = BACCreditCard._date(cleaned_transactions[0])
        ends = BACCreditCard._date(cleaned_transactions[-1])
        logger.debug("from %d to %d", starts, ends)
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            logger.info("Applied transactions: %d", applied_transactions)

    def insert_transaction(self, transaction: dict) -> list[int]:
        """Actual single insert."""
        logger = config_logger("entities/bac.py")
        try:
            _asset = self._asset(transaction)
            if not _asset:
                logger.warning("Asset not found for this transaction: %s", transaction)
                return []
            transaction_insert = TransactionInsertObject(
                amount=BACCreditCard._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=self._date(transaction),
                external_id=self._external_id(transaction),
                notes=BACCreditCard._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                transactions=transaction_insert,
                apply_rules=True,
                skip_duplicates=False,
                debit_as_negative=BACCreditCard._debit_as_negative(transaction),
                skip_balance_update=False,
            )
            if result:
                logger.info("Applied transaction: %s-%s", result, self._external_id(transaction))
        except (ValueError, LunchMoneyHTTPError) as exception:
            logger.debug("Could not applied transaction: %s", transaction)
            logger.debug("Exception: %s", exception)
            return []
        return result

    @staticmethod
    def clean_transaction(transaction: dict) -> dict:
        """Parse raw row and build TransactionInsertObject."""
        try:
            day, month, year = transaction["Date"].split("/")
            datetime.date(int(year), int(month), int(day))
        except ValueError:
            return {}
        return transaction

    @staticmethod
    def _date(transaction: dict) -> datetime.date:
        day, month, year = transaction["Date"].split("/")
        return datetime.date(int(year), int(month), int(day))

    def _asset(self, transaction: dict) -> AssetsObject | None:
        crc = _float(transaction["Local"])
        usd = _float(transaction["Dollars "])
        if crc:
            return next(a for a in self.assets if a.currency == "crc")
        if usd:
            return next(a for a in self.assets if a.currency == "usd")
        return None

    @staticmethod
    def _amount(transaction: dict) -> float:
        crc = _float(transaction["Local"])
        usd = _float(transaction["Dollars "])
        return abs(crc or usd)

    @staticmethod
    def _notes(transaction: dict) -> str:
        return _str(transaction[""])

    def _external_id(self, transaction: dict) -> str:
        return slugify(
            " ".join(
                [
                    self._date(transaction).isoformat(),
                    self._notes(transaction),
                    str(self._amount(transaction)),
                ],
            ),
        )

    @staticmethod
    def _debit_as_negative(transaction: dict) -> bool:
        return (_float(transaction["Local"]) or _float(transaction["Dollars "])) < 0
