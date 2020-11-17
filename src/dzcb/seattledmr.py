import argparse
from pathlib import Path
import os

import requests

SEATTLE_DMR_REPEATERS = "http://seattledmr.org/ConfigBuilder/Digital-Repeaters-Seattle-addon.csv"
SEATTLE_DMR_TALKGROUPS = "http://seattledmr.org/ConfigBuilder/Talkgroups-Seattle-addon.csv"
REPEATER_FILENAME = "Digital-Repeaters__SeattleDMR.csv"
TALKGROUPS_FILENAME = "Talkgroups__SeattleDMR.csv"


def cache_repeaters(output_dir):
    repeaters = requests.get(SEATTLE_DMR_REPEATERS)
    repeaters.raise_for_status()
    talkgroups = requests.get(SEATTLE_DMR_TALKGROUPS)
    talkgroups.raise_for_status()
    outpath = Path(output_dir)
    (outpath / REPEATER_FILENAME).write_text(repeaters.text)
    (outpath / TALKGROUPS_FILENAME).write_text(talkgroups.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    args = parser.parse_args()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    cache_repeaters(args.output_dir)
