import argparse
import sys

from . import Codeplug, DigitalRepeater

parser = argparse.ArgumentParser(description="dzcb: DMR Zone Channel Builder")
parser.add_argument(
    "--based-on",
    type=argparse.FileType("r"),
    default=None,
    help="JSON file to take settings from",
)
parser.add_argument(
    "outfile", type=argparse.FileType("w"), help="Write JSON code plug to this file"
)
args = parser.parse_args()

args.outfile.write(
    Codeplug.from_repeaters(DigitalRepeater.from_cache_all()).to_json(
        based_on=args.based_on
    )
)
