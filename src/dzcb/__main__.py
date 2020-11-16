"""
dzcb main program
"""

import argparse
from importlib_resources import contents, files
from pathlib import Path
import os
import sys

import dzcb.k7abd
import dzcb.farnsworth
import dzcb.gb3gf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="dzcb: DMR Zone Channel Builder")
    parser.add_argument(
        "--farnsworth-template-json",
        type=argparse.FileType("r"),
        default=None,
        help="JSON file to take Farnsworth settings from",
    )
    parser.add_argument("k7abd_input_dir", help="Read K7ABD CSV files from this dir")
    parser.add_argument(
        "outdir", help="Write code plug files to this directory"
    )
    args = parser.parse_args()
    cp = dzcb.k7abd.Codeplug_from_k7abd(args.k7abd_input_dir)

    outdir = Path(args.outdir)
    if not outdir.exists():
        outdir.mkdir()

    # Farnsworth JSON - TYT et. al w/ Zone Import!
    outfile = outdir / "farnsworth.json"
    outfile.write_text(
        dzcb.farnsworth.Codeplug_to_json(
            cp.expand_static_talkgroups(),
            based_on=args.farnsworth_template_json,
        )
    )

    # GB3GF CSV - Radioddity GD77/OpenGD77, TYT MD-380, MD-9600, Baofeng DM1801, RD-5R
    # XXX: Only support OpenGD77 at the moment
    gd77_outdir = Path(args.outdir) / "gb3gf_opengd77" 
    if not gd77_outdir.exists():
        gd77_outdir.mkdir()
    dzcb.gb3gf.Codeplug_to_gb3gf_opengd77_csv(cp, gd77_outdir)

"""

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
"""
