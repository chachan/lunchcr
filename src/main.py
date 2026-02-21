"""lunchcr entrypoint."""

import argparse
import configparser
import pathlib

from entities.bac import BACAccount, BACCreditCard
from entities.scotiabank import ScotiabankAccount, ScotiabankCreditCard
from utils import LunchMoneyCR, config_logger

ENTITIES = [
    BACAccount,
    BACCreditCard,
    ScotiabankCreditCard,
    ScotiabankAccount,
]


def main(datapath: pathlib.Path, cfg: configparser.ConfigParser) -> None:
    """Entrypoint."""
    access_token = cfg["lunchmoney"].get("access_token", "")
    lunch_money = LunchMoneyCR(access_token)
    logger = config_logger("main.py")

    for file_path in pathlib.Path(datapath).iterdir():
        if not file_path.match("*.csv") and not file_path.match("*.txt"):
            continue
        logger.info("\nFile: %s", file_path)
        inferred_assets = []
        inferred_entity = None

        for e in ENTITIES:
            inferred_assets = e.infer(lunch_money, file_path)
            inferred_entity = e
            if inferred_assets:
                break

        if not inferred_entity:
            logger.error("Entity not infered.")
            return

        for asset in inferred_assets:
            fields = ["id", "institution_name", "name", "display_name"]
            output = " | ".join([str(getattr(asset, f)) for f in fields])
            logger.info("Entity Detected: %s", output)
        if not inferred_assets:
            logger.warning("No entity detected for this file")
            continue
        instance = inferred_entity(lunch_money, file_path)
        instance.insert_transactions()


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.cfg")

    parser = argparse.ArgumentParser()
    parser.add_argument("datapath", type=pathlib.Path)
    args = parser.parse_args()

    main(args.datapath, config)
