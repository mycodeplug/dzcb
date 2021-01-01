"""
dzcb main program
"""

import argparse
import json
from importlib_resources import contents, files
from pathlib import Path
import os
import shutil
import sys

import dzcb.data
import dzcb.farnsworth
import dzcb.gb3gf
import dzcb.k7abd
import dzcb.model
import dzcb.pnwdigital
import dzcb.repeaterbook
import dzcb.seattledmr


def append_dir_and_create(path, component=None):
    new_path = path
    if component:
        new_path = new_path / component
    if not new_path.exists():
        new_path.mkdir()
    return new_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="dzcb: DMR Zone Channel Builder")
    parser.add_argument(
        "--pnwdigital",
        action="store_true",
        help="Fetch the latest pnwdigital K7ABD input files",
    )
    parser.add_argument(
        "--seattledmr",
        action="store_true",
        help="Fetch the latest seattledmr K7ABD input files",
    )
    parser.add_argument(
        "--repeaterbook-proximity-csv",
        type=argparse.FileType("r"),
        default=None,
        help="Fetch repeaters within X distance of POIs defined in a CSV file"
    )
    parser.add_argument(
        "--default-k7abd",
        action="store_true",
        help="Include bundled K7ABD input files (simplex + unlicensed)",
    )
    parser.add_argument(
        "--k7abd",
        nargs="*",
        help="Specify one or more local directories containing K7ABD CSV files"
    )
    parser.add_argument(
        "--farnsworth-template-json",
        type=argparse.FileType("r"),
        default=None,
        help="JSON file to take Farnsworth settings from. If no json file, defaults will " 
             "be used for each supported radio type.",
    )
    parser.add_argument(
        "--scanlists-json",
        type=argparse.FileType("r"),
        default=None,
        help="JSON dict mapping scanlist name to list of channel names.",
    )
    parser.add_argument(
        "--order-json",
        type=argparse.FileType("r"),
        default=None,
        help="JSON dict specifying zone and talkgroup orderings."
    )
    parser.add_argument(
        "outdir", help="Write code plug files to this directory"
    )
    args = parser.parse_args()

    outdir = append_dir_and_create(Path(args.outdir))
    cache_dir = append_dir_and_create(outdir, "cache")

    # fetch data from the internet
    if args.repeaterbook_proximity_csv:
        if "REPEATERBOOK_USER" not in os.environ or "REPEATERBOOK_PASSWD" not in os.environ:
            print("Supply REPEATERBOOK_USER and REPEATERBOOK_PASSWD in environment")
            sys.exit(2)
        proximity_csv = args.repeaterbook_proximity_csv.read().splitlines()
        rbcache = append_dir_and_create(cache_dir, "repeaterbook")
        dzcb.repeaterbook.cache_zones_with_proximity(proximity_csv, rbcache)
        dzcb.repeaterbook.zones_to_k7abd(proximity_csv, rbcache, cache_dir)

    if args.pnwdigital:
        dzcb.pnwdigital.cache_repeaters(cache_dir)

    if args.seattledmr:
        dzcb.seattledmr.cache_repeaters(cache_dir)

    if args.default_k7abd:
        shutil.copytree(files(dzcb.data) / "k7abd", cache_dir, dirs_exist_ok=True)

    if args.k7abd:
        # copy any additional CSV directories into the cache_dir
        for abd_dir in args.k7abd:
            shutil.copytree(abd_dir, cache_dir, dirs_exist_ok=True)

    # load additional data files or defaults
    if args.scanlists_json is None:
        scanlists = json.loads(files(dzcb.data).joinpath("scanlists.json").read_text())
    else:
        scanlists = json.load(args.scanlists_json)

    if args.order_json is None:
        order = json.loads(files(dzcb.data).joinpath("order.json").read_text())
    else:
        order = json.load(args.order_json)
    zone_order = order.get("zone", {}).get("default", [])
    zone_order_expanded = order.get("zone", {}).get("expanded", [])
    exclude_zones_expanded = order.get("zone", {}).get("exclude_expanded", [])
    static_talkgroup_order = order.get("static_talkgroup", [])

    # create codeplug from a directory of k7abd CSVs
    cp = dzcb.k7abd.Codeplug_from_k7abd(cache_dir).order_grouplists(static_talkgroup_order=static_talkgroup_order)

    # expand static_talkgroups into channel per talkgroup / zone per repeater
    fw_cp = cp.expand_static_talkgroups(
        static_talkgroup_order=static_talkgroup_order).order_zones(
        zone_order=zone_order_expanded,
        exclude_zones=exclude_zones_expanded,
    )

    # add custom scanlists after static TG expansion
    for sl_name, channels in scanlists.items():
        sl = dzcb.model.ScanList.from_names(name=sl_name, channel_names=channels)
        cp.scanlists.append(sl)
        fw_cp.scanlists.append(sl)

    # Farnsworth JSON - TYT et. al w/ Zone Import!
    farnsworth_templates = []
    if args.farnsworth_template_json is None:
        # Iterate through all farnsworth templates, generating codeplug for each
        for f in (files(dzcb.data) / "farnsworth").iterdir():
            if not str(f).endswith(".json"):
                continue
            farnsworth_templates.append((f.name, f.open("r")))
    else:
        farnsworth_templates.append(("farnsworth.json", args.farnsworth_template_json))

    for fname, fh in farnsworth_templates:
        outfile = outdir / fname
        outfile.write_text(
            dzcb.farnsworth.Codeplug_to_json(
                cp=fw_cp,
                based_on=fh,
            )
        )

    # GB3GF CSV - Radioddity GD77/OpenGD77, TYT MD-380, MD-9600, Baofeng DM1801, RD-5R
    # XXX: Only support OpenGD77 at the moment
    gd77_outdir = Path(args.outdir) / "gb3gf_opengd77" 
    if not gd77_outdir.exists():
        gd77_outdir.mkdir()
    dzcb.gb3gf.Codeplug_to_gb3gf_opengd77_csv(
        cp.order_zones(zone_order=zone_order),
        output_dir=gd77_outdir,
    )
