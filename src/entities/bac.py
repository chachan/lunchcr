"""BAC parser classes"""

from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base


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
        return bool(instance.asset)

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
        for each in raw_transactions:
            self.insert_transaction(each)

    def insert_transaction(self, transaction):
        """Actual single insert"""
        _str = lambda x: x.strip()
        _float = lambda x: float(x.strip())
        try:
            balance = transaction["Transaction balance"]
            if not balance:
                return
            day, month, year = _str(transaction["Transaction date"]).split("/")
            debit = _float(transaction["Transaction debit"])
            credit = _float(transaction["Transaction credit"])
            amount = debit or credit
            notes = _str(transaction["Description of transactions"])
            external_id = slugify(
                " ".join(
                    [
                        _str(transaction["Transaction reference"]),
                        balance,
                        notes,
                        str(amount),
                    ]
                )
            )
            transaction = TransactionInsertObject(
                amount=amount,
                asset_id=self.asset.id,
                currency=self.asset.currency,
                date=f"{year}-{month}-{day}",
                external_id=external_id,
                notes=notes,
                payee="",
            )
            result = self.lunch_money.insert_transactions(
                debit_as_negative=credit > 0,
                skip_balance_update=False,
                skip_duplicates=False,
                transactions=transaction,
            )
            if len(result):
                print(f"Applied transaction: {result}")
            else:
                print(f"Could not applied transaction: {transaction}")
                return
        except ValueError:
            print(f"ValueError | could not applied transaction: {transaction}")
            return
