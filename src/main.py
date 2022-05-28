"""lunchcr entrypoint"""
import argparse
import configparser
import os
import pathlib

from lunchable import LunchMoney

from entities.bac import BACAccount, BACCreditCard
from entities.payoneer import PayoneerAccount
from entities.scotiabank import ScotiabankAccount, ScotiabankCreditCard

ENTITIES = [
    BACAccount,
    BACCreditCard,
    PayoneerAccount,
    ScotiabankCreditCard,
    ScotiabankAccount,
]


class LunchMoneyCR(LunchMoney):  # pylint: disable=too-many-ancestors
    """LunchMoney wrapper to include custom logic"""

    def __init__(self, access_token):
        super().__init__(access_token)
        self.cached_assets = self.get_assets()


def main(datapath, cfg):
    """main handler"""
    access_token = cfg["lunchmoney"].get("access_token")
    lunch_money = LunchMoneyCR(access_token)
    files = [each for each in os.listdir(datapath) if each.endswith(".csv")]
    if not files:
        print(f"Could not find csv files in {datapath}")

    for file_name in files:
        print("\n")
        inferred_assets = []
        inferred_entity = None
        for e in ENTITIES:
            inferred_assets = e.infer(lunch_money, file_name)
            inferred_entity = e
            if inferred_assets:
                break

        print(f"File: {file_name}")
        print("Detected assets:")
        for asset in inferred_assets:
            fields = ["id", "institution_name", "name", "display_name"]
            output = " | ".join([str(getattr(asset, f)) for f in fields])
            print(f"- {output}")
        if not inferred_assets:
            print("- No entity detected for this file")
            continue
        instance = inferred_entity(lunch_money, file_name)
        instance.insert_transactions()


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.cfg")

    parser = argparse.ArgumentParser()
    parser.add_argument("datapath", type=pathlib.Path)
    args = parser.parse_args()

    main(args.datapath, config)
