"""Payoneer parser classes"""

import click
from lunchable import TransactionInsertObject
from slugify import slugify
from utils import _str

from entities.base import Base


class PayoneerAccount(Base):
    """Parser for Bank Accounts"""

    FILE_ENCODING = "utf-8"
    TRANSACTION_FIELD_NAMES = [
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
        return instance.asset

    def define_asset(self):
        """Define asset or accounr target in lunch money"""
        rows = self.read_rows(
            PayoneerAccount.TRANSACTION_FIELD_NAMES, self.FILE_ENCODING
        )
        try:
            int(rows[1].get("Transaction ID"))
        except ValueError:
            return False
        for asset in self.lunch_money.cached_assets:
            if asset.name == "PAYONEER":
                self.asset = asset
                break

    def insert_transactions(self):
        """Insert transactions into an already define lunch money asset"""
        if not self.asset:
            self.define_asset()

        rows = self.read_rows(self.TRANSACTION_FIELD_NAMES, encoding=self.FILE_ENCODING)

        raw_transactions = rows[1:]
        print(f"Raw transactions detected: {len(raw_transactions)}")
        cleaned_transactions = list(
            filter(PayoneerAccount.clean_transaction, raw_transactions)
        )
        cleaned_transactions.reverse()
        print(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = PayoneerAccount._date(cleaned_transactions[0])
        ends = PayoneerAccount._date(cleaned_transactions[-1])
        print(f"from {starts} to {ends}")
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            print(f"Applied transactions: {applied_transactions}")

    def insert_transaction(self, transaction):
        """Actual single insert"""
        try:
            transaction_insert = TransactionInsertObject(
                amount=PayoneerAccount._amount(transaction),
                asset_id=self.asset.id,
                currency=self.asset.currency,
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
                print(
                    f"Applied transaction: {result}-{PayoneerAccount._external_id(transaction)}"
                )
            return result
        except ValueError as exception:
            print(f"ValueError | could not applied transaction: {transaction}")
            print(exception)
            return

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
