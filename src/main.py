import argparse
import pathlib
import os

from lunchable import LunchMoney

from entities.bac import BACAccount

ENTITIES = [BACAccount]


def main(datapath):
    files = os.listdir(datapath)
    print(files)
    # file_name = ""
    # entity = [entity.infer(file_name) for entity in ENTITIES]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("datapath", type=pathlib.Path)
    args = parser.parse_args()

    main(args.datapath)
