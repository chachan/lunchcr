from lunchable import TransactionInsertObject
from slugify import slugify

from entities.base import Base

TRANSACTION_FIELD_NAMES = [
    "Transaction date",
    "Transaction reference",
    "Transaction codes",
    "Description of transactions",
    "Transaction debit",
    "Transaction credit",
    "Transaction balance",
]

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


class BACAccount(Base):
    def __init__(self, lunch_money, file_name):
        self.lunch_money = lunch_money
        self.file_name = file_name

    @staticmethod
    def infer(file_name):
        pass

    def define_asset(self, rows):
        rows = self.read_rows(ASSET_FIELD_NAMES)
        product = rows[1]["Product"].strip()
        assets = self.lunch_money.get_assets()
        by_name = lambda a: a.name == product
        filtered_assets = list(filter(by_name, assets))
        if len(filtered_assets) != 1:
            raise ValueError("Can't define asset to apply")
        print(f"setting asset: {filtered_assets[0]}")
        self.asset = filtered_assets[0]

    def insert_transactions(self):
        if not self.asset:
            self.define_asset()

        rows = self.read_rows(TRANSACTION_FIELD_NAMES)

        raw_transactions = rows[4:]
        s = lambda x: x.strip()
        f = lambda x: float(x.strip())
        for each in raw_transactions:
            try:
                balance = each["Transaction balance"]
                if not balance:
                    continue
                day, month, year = s(each["Transaction date"]).split("/")
                debit = f(each["Transaction debit"])
                credit = f(each["Transaction credit"])
                amount = debit or credit
                notes = s(each["Description of transactions"])
                external_id = slugify(
                    " ".join(
                        [
                            s(each["Transaction reference"]),
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
                    print(f"applied transaction: {result}")
                else:
                    print(f"could not applied transaction: {transaction}")
                    break
            except ValueError:
                print(f"ValueError | could not applied transaction: {each}")
                break
