"""BAC parser classes"""

import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import _float, _str


class BACAccount(Base):
    """Parser for Bank Accounts"""

    ASSET_FIELD_NAMES = [
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
    FILE_ENCODING = "cp1252"
    TRANSACTION_FIELD_NAMES = [
        "Transaction date",
        "Transaction reference",
        "Transaction codes",
        "Description of transactions",
        "Transaction debit",
        "Transaction credit",
        "Transaction balance",
    ]

    @staticmethod
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid BAC Account CSV file"""
        instance = BACAccount(lunch_money, file_name)
        instance.define_asset()
        return instance.asset

    def define_asset(self):
        """Define asset or accounr target in lunch money"""
        rows = self.read_rows(self.ASSET_FIELD_NAMES, self.FILE_ENCODING)
        product = rows[1]["Product"].strip()
        by_name = lambda a: a.name == product
        filtered_assets = list(filter(by_name, self.lunch_money.cached_assets))
        if len(filtered_assets) == 1:
            self.asset = filtered_assets[0]

    def insert_transactions(self):
        """Insert transactions into an already define lunch money asset"""
        if not self.asset:
            self.define_asset()

        rows = self.read_rows(self.TRANSACTION_FIELD_NAMES, encoding=self.FILE_ENCODING)

        raw_transactions = rows[4:]
        print(f"Raw transactions detected: {len(raw_transactions)}")
        cleaned_transactions = list(
            filter(BACAccount.clean_transaction, raw_transactions)
        )
        print(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = "-".join(BACAccount._date(cleaned_transactions[0]))
        ends = "-".join(BACAccount._date(cleaned_transactions[-1]))
        print(f"from {starts} to {ends} (DD/MM/YYYY)")
        if click.confirm("Do you want to continue?"):
            applied_transactions = 0
            for transaction in cleaned_transactions:
                result = self.insert_transaction(transaction)
                applied_transactions += 1 if result else 0
            print(f"Applied transactions: {applied_transactions}")

    def insert_transaction(self, transaction):
        """Actual single insert"""
        try:
            day, month, year = BACAccount._date(transaction)
            debit_as_negative = BACAccount._credit(transaction) > 0
            external_id = BACAccount._external_id(transaction)
            transaction_insert = TransactionInsertObject(
                amount=BACAccount._amount(transaction),
                asset_id=self.asset.id,
                currency=self.asset.currency,
                date=f"{year}-{month}-{day}",
                external_id=external_id,
                notes=BACAccount._notes(transaction),
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                debit_as_negative=debit_as_negative,
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction_insert,
            )
            if result:
                print(f"Applied transaction: {result}-{external_id}")
            else:
                print(f"Could not applied transaction: {transaction}")
            return result
        except ValueError as exception:
            print(f"ValueError | could not applied transaction: {transaction}")
            print(exception)
            return

    @staticmethod
    def clean_transaction(transaction):
        """Parse raw row and build TransactionInsertObject"""
        return transaction if BACAccount._balance(transaction) else None

    @staticmethod
    def _external_id(transaction):
        return slugify(
            " ".join(
                [
                    _str(transaction["Transaction reference"]),
                    BACAccount._balance(transaction),
                    BACAccount._notes(transaction),
                    str(BACAccount._amount(transaction)),
                ]
            )
        )

    @staticmethod
    def _balance(transaction):
        return transaction["Transaction balance"]

    @staticmethod
    def _notes(transaction):
        return _str(transaction["Description of transactions"])

    @staticmethod
    def _credit(transaction):
        return _float(transaction["Transaction credit"])

    @staticmethod
    def _amount(transaction):
        debit = _float(transaction["Transaction debit"])
        credit = BACAccount._credit(transaction)
        return debit or credit

    @staticmethod
    def _date(transaction):
        return _str(transaction["Transaction date"]).split("/")
