import csv

from lunchable import LunchMoney, TransactionInsertObject


def insert_transactions(lunch_money, asset):
    with open("sample.csv", encoding="cp1252") as csvfile:
        fieldnames = [
            "Transaction date",
            "Transaction reference",
            "Transaction codes",
            "Description of transactions",
            "Transaction debit",
            "Transaction credit",
            "Transaction balance",
        ]
        reader = csv.DictReader(csvfile, fieldnames)
        rows = list(reader)
        raw_transactions = rows[4:]
        s = lambda x: x.strip()
        f = lambda x: float(x.strip())
        for each in raw_transactions:
            try:
                if not each["Transaction balance"]:
                    continue
                day, month, year = s(each["Transaction date"]).split("/")
                debit = f(each["Transaction debit"])
                credit = f(each["Transaction credit"])
                transaction = TransactionInsertObject(
                    amount=debit or credit,
                    asset_id=asset.id,
                    currency=asset.currency,
                    date=f"{year}-{month}-{day}",
                    external_id=s(each["Transaction reference"]),
                    notes=s(each["Description of transactions"]),
                    payee="",
                )
                result = lunch_money.insert_transactions(
                    debit_as_negative=credit > 0,
                    skip_balance_update=False,
                    transactions=transaction,
                )
                if len(result):
                    print(f"applied transaction: {result}")
                else:
                    print(f"could not applied transaction: {each}")
            except ValueError:
                print(f"could not applied transaction: {each}")


def define_asset(lunch_money):
    with open("sample.csv", encoding="cp1252") as csvfile:
        fieldnames = [
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
        reader = csv.DictReader(csvfile, fieldnames)
        rows = list(reader)
        product = rows[1]["Product"].strip()
        assets = lunch_money.get_assets()
        by_name = lambda a: a.name == product
        filtered_assets = list(filter(by_name, assets))
        if len(filtered_assets) != 1:
            raise ValueError("Can't define asset to apply")
        print(f"setting asset: {filtered_assets[0]}")
        return filtered_assets[0]


def main():
    lunch_money = LunchMoney(access_token="")
    asset = define_asset(lunch_money)
    insert_transactions(lunch_money, asset)

    # categories = lunch_money.get_categories()
    # print(categories)


if __name__ == "__main__":
    main()
