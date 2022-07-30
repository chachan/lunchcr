"""BAC parser classes"""
import datetime

import click
from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base
from utils import _float, _str


class BACAccount(Base):
    """Parser for Bank Accounts"""

    asset_field_names = [
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
    file_encoding = "cp1252"
    transaction_field_names = [
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
        instance.define_assets()
        return instance.assets

    def define_assets(self):
        """Define assets or accounr target in lunch money"""
        rows = self.read_rows(BACAccount.asset_field_names)
        product = _str(rows[1].get("Product", ""))
        by_name = lambda a: a.name == product
        filtered_assets = list(filter(by_name, self.lunch_money.cached_assets))
        if len(filtered_assets) == 1:
            self.assets = filtered_assets[0]

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_assets()

        rows = self.read_rows(self.transaction_field_names)

        raw_transactions = rows[4:]
        print(f"Raw transactions detected: {len(raw_transactions)}")
        cleaned_transactions = list(filter(BACAccount.clean_transaction, raw_transactions))
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
            _asset = self.assets[0]
            transaction_insert = TransactionInsertObject(
                amount=BACAccount._amount(transaction),
                asset_id=_asset.id,
                currency=_asset.currency,
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
            return result
        except ValueError as exception:
            print(f"ValueError | could not applied transaction: {transaction}")
            print(exception)
            return None

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


class BACCreditCard(Base):
    """Parser for Credit Cards"""

    asset_field_names = [
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
    file_encoding = "cp1252"
    transaction_field_names = ["Date", "", "Local", "Dollars "]

    @staticmethod
    def infer(lunch_money, file_name):
        """Tells if file_name is a valid BAC credit card CSV file"""
        instance = BACCreditCard(lunch_money, file_name)
        instance.define_asset()
        return instance.assets

    def define_asset(self):
        """Define assets or accounr target in lunch money"""
        rows = self.read_rows(BACCreditCard.asset_field_names)
        product = _str(rows[1]["Pro000000000000duct"])
        by_name = lambda a: a.name == product
        self.assets = list(filter(by_name, self.lunch_money.cached_assets))

    def insert_transactions(self):
        """Insert transactions into an already define lunch money assets"""
        if not self.assets:
            self.define_asset()

        rows = self.read_rows(self.transaction_field_names)

        cleaned_transactions = list(filter(BACCreditCard.clean_transaction, rows))
        cleaned_transactions.sort(key=BACCreditCard._date)
        print(f"Cleaned transactions: {len(cleaned_transactions)}")
        starts = BACCreditCard._date(cleaned_transactions[0])
        ends = BACCreditCard._date(cleaned_transactions[-1])
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
            _asset = self._asset(transaction)
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
                debit_as_negative=BACCreditCard._debit_as_negative(transaction),
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction_insert,
            )
            if result:
                print(f"Applied transaction: {result}-{self._external_id(transaction)}")
            return result
        except ValueError as exception:
            print(f"ValueError | could not applied transaction: {transaction}")
            print(exception)
            return None

    @staticmethod
    def clean_transaction(transaction):
        """Parse raw row and build TransactionInsertObject"""
        try:
            day, month, year = transaction["Date"].split("/")
            datetime.date(int(year), int(month), int(day))
            return transaction
        except ValueError:
            return None

    @staticmethod
    def _date(transaction):
        day, month, year = transaction["Date"].split("/")
        return f"{year}-{month}-{day}"

    def _asset(self, transaction):
        crc = _float(transaction["Local"])
        usd = _float(transaction["Dollars "])
        if crc:
            return [a for a in self.assets if a.currency == "crc"][0]
        if usd:
            return [a for a in self.assets if a.currency == "usd"][0]
        return None

    @staticmethod
    def _amount(transaction):
        crc = _float(transaction["Local"])
        usd = _float(transaction["Dollars "])
        return abs(crc or usd)

    @staticmethod
    def _notes(transaction):
        return _str(transaction[""])

    def _external_id(self, transaction):
        return slugify(
            " ".join(
                [
                    self._date(transaction),
                    self._notes(transaction),
                    str(self._amount(transaction)),
                ]
            )
        )

    @staticmethod
    def _debit_as_negative(transaction):
        return (_float(transaction["Local"]) or _float(transaction["Dollars "])) < 0
