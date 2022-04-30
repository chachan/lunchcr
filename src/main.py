import argparse
import configparser
import os
import pathlib

from lunchable import LunchMoney

from entities.bac import BACAccount

ENTITIES = [BACAccount]


def main(datapath, config):
    access_token = config["lunchmoney"].get("access_token")
    lunch_money = LunchMoney(access_token)
    files = [each for each in os.listdir(datapath) if each.endswith(".csv")]
    if not files:
        print(f"could not find csv files in {datapath}")

    # entity = [entity.infer(file_name) for entity in ENTITIES]


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.cfg")

    parser = argparse.ArgumentParser()
    parser.add_argument("datapath", type=pathlib.Path)
    args = parser.parse_args()

    main(args.datapath, config)
