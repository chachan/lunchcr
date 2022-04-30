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
        print("-")
        entities = [
            entity for entity in ENTITIES if entity.infer(lunch_money, file_name)
        ]
        print(f"File: {file_name}")
        if len(entities) == 1:
            print(f"Detected: {entities[0].__name__}")
            instance = entities[0](lunch_money, file_name)
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
