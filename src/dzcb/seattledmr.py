import argparse
import logging
from pathlib import Path
import os
import re

import requests

logger = logging.getLogger(__name__)

SEATTLE_DMR_REPEATERS = (
    "http://seattledmr.org/ConfigBuilder/Digital-Repeaters-Seattle-addon.csv"
)
SEATTLE_DMR_TALKGROUPS = (
    "http://seattledmr.org/ConfigBuilder/Talkgroups-Seattle-addon.csv"
)
REPEATER_FILENAME = "Digital-Repeaters__SeattleDMR.csv"
TALKGROUPS_FILENAME = "Talkgroups__SeattleDMR.csv"


def cache_repeaters(output_dir):
    repeaters = requests.get(SEATTLE_DMR_REPEATERS)
    repeaters.raise_for_status()
    talkgroups = requests.get(SEATTLE_DMR_TALKGROUPS)
    talkgroups.raise_for_status()
    outpath = Path(output_dir)
    rp_out = outpath / REPEATER_FILENAME
    with rp_out.open("w", newline="") as f:
        # XXX: Hacks: need to fix upstream
        for line in repeaters.text.splitlines(True):
            line = line.replace("BayNet", "Baynet").replace("PNWR", "PNW Rgnl 2")
            line = line.replace("Wash 1", "Washington 1").replace(
                "Wash 2", "Washington 2"
            )
            f.write(line)
    logger.info("Cache SeattleDMR k7abd zones to '%s'", rp_out)

    tg_out = outpath / TALKGROUPS_FILENAME
    with tg_out.open("w", newline="") as f:
        # XXX: Hacks: need to fix upstream
        for line in talkgroups.text.splitlines(True):
            line = re.sub(r"Link([0-9]+)", r"Link \1", line)
            f.write(line)
        f.write("TAC 8-2,8958\n")
    logger.info("Cache SeattleDMR k7abd talkgroups to '%s'", tg_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    args = parser.parse_args()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    cache_repeaters(args.output_dir)
