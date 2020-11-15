import argparse
from importlib_resources import contents, files
import os
import sys

from . import AnalogRepeater, Codeplug, DigitalRepeater
from . import data
from .data import k7abd

parser = argparse.ArgumentParser(description="dzcb: DMR Zone Channel Builder")
parser.add_argument(
    "--based-on",
    type=argparse.FileType("r"),
    default=None,
    help="JSON file to take settings from",
)
parser.add_argument(
    "outdir", help="Write code plug files to this directory"
)
args = parser.parse_args()

analog_zones = {}
for fname in contents(data.k7abd):
    if not fname.startswith("Analog__") or not fname.endswith(".csv"):
        continue
    analog_zones.update(
        AnalogRepeater.from_k7abd_csv(
            files(data.k7abd).joinpath(
                fname
            ).read_text().splitlines()
        )
    )
cp = Codeplug.from_repeaters(
        repeaters=DigitalRepeater.from_k7abd_csv(
            digital_repeaters_csv=files(data.k7abd).joinpath(
                "Digital-Repeaters__PNW-all-2020-11-12.csv"
            ).read_text().splitlines(),
            talkgroups_csv=files(data.k7abd).joinpath(
                "Talkgroups__PNW-all-2020-11-12.csv"
            ).read_text().splitlines(),
        ),
        analog_zones=analog_zones,
)
with open(os.path.join(args.outdir, "farnsworth.json"), "w") as f:
    f.write(
        cp.to_json(based_on=args.based_on)
    )
cp77 = Codeplug.from_repeaters(
        repeaters=DigitalRepeater.from_k7abd_csv(
            files(data.k7abd).joinpath(
                "Digital-Repeaters__PNW-all-2020-11-12.csv"
            ).read_text().splitlines(),
            talkgroups_csv=files(data.k7abd).joinpath(
                "Talkgroups__PNW-all-2020-11-12.csv"
            ).read_text().splitlines(),
        ),
        analog_zones=analog_zones,
        channel_per_talkgroup=False,
        single_zone_name="PNWDigital",
)
cp77.to_gb3gf_opengd77_csv(args.outdir)
