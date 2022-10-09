"""Payoneer parser classes"""
import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import _str, config_logger

LOGGER = config_logger("entities/payoneer.py")


class PayoneerAccount(Base):
    """Parser for Bank Accounts"""

    transaction_field_names = [
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
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid Payoneer Account CSV file"""
        instance = PayoneerAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self):
        """Define assets or accounr target in lunch money"""
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

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(PayoneerAccount.transaction_field_names)

        raw_transactions = rows[1:]
        LOGGER.debug(f"Raw transactions detected: {len(raw_transactions)}")
        cleaned_transactions = list(filter(PayoneerAccount.clean_transaction, raw_transactions))
        cleaned_transactions.reverse()
        LOGGER.debug(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = PayoneerAccount._date(cleaned_transactions[0])
        ends = PayoneerAccount._date(cleaned_transactions[-1])
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
                amount=PayoneerAccount._amount(transaction).replace(",", ""),
                asset_id=_asset.id,
                currency=_asset.currency,
                date=PayoneerAccount._date(transaction),
                external_id=PayoneerAccount._external_id(transaction),
                notes=PayoneerAccount._notes(transaction),
                payee="",
            )
            _debit_as_negative = PayoneerAccount._debit_as_negative(transaction)
            result = self.lunch_money.insert_transactions(
                debit_as_negative=_debit_as_negative,
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction_insert,
            )
            if result:
                LOGGER.info(f"Applied transaction: {result}-{PayoneerAccount._external_id(transaction)}")
            return result
        except ValueError as exception:
            LOGGER.error(f"could not applied transaction: {transaction}")
            LOGGER.error(exception)
            return None

    @staticmethod
    def clean_transaction(transaction):
        """Parse raw row and build TransactionInsertObject"""
        return transaction

    @staticmethod
    def _amount(transaction):
        return transaction["Credit Amount"] or transaction["Debit Amount"]

    @staticmethod
    def _date(transaction):
        month, day, year = _str(transaction["Transaction Date"]).split("/")
        return f"{year}-{month}-{day}"

    @staticmethod
    def _external_id(transaction):
        return slugify(
            " ".join(
                [
                    _str(transaction["Transaction ID"]),
                    PayoneerAccount._notes(transaction),
                    _str(PayoneerAccount._amount(transaction)),
                ]
            )
        )

    @staticmethod
    def _notes(transaction):
        return transaction["Description"]

    @staticmethod
    def _debit_as_negative(transaction):
        return bool(transaction["Credit Amount"])
