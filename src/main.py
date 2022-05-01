"""lunchcr entrypoint"""

import argparse
import configparser
import os
import pathlib

from lunchable import LunchMoney

from entities.bac import BACAccount

ENTITIES = [BACAccount]


class LunchMoneyCR(LunchMoney):
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
        print("\n-")
        inferred_asset = None
        inferred_entity = None
        for e in ENTITIES:
            inferred_asset = e.infer(lunch_money, file_name)
            inferred_entity = e
            if inferred_asset:
                break

        # entities = [e for e in ENTITIES if e.infer(lunch_money, file_name)]
        print(f"File: {file_name}")
        if inferred_asset:
            fields = ["id", "institution_name", "name", "display_name"]
            output = " | ".join([str(getattr(inferred_asset, f)) for f in fields])
            print(f"Detected: {output}")
            instance = inferred_entity(lunch_money, file_name)
            instance.insert_transactions()
        else:
            print("No entity detected for this file")


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.cfg")

    parser = argparse.ArgumentParser()
    parser.add_argument("datapath", type=pathlib.Path)
    args = parser.parse_args()

    main(args.datapath, config)
