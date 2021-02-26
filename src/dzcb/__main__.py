"""
dzcb main program
"""

import argparse
import json
from importlib_resources import contents, files
import logging
from pathlib import Path
import os
import shutil

from dzcb import __version__
import dzcb.anytone
import dzcb.data
import dzcb.farnsworth
import dzcb.gb3gf
import dzcb.k7abd
import dzcb.log
import dzcb.model
import dzcb.pnwdigital
import dzcb.repeaterbook
import dzcb.seattledmr


logger = logging.getLogger("dzcb")


def append_dir_and_create(path, component=None):
    new_path = path
    if component:
        new_path = new_path / component
    new_path.mkdir(parents=True, exist_ok=True)
    return new_path


def cache_user_or_default_text(object_name, user_path, default_path, cache_dir):
    """
    Read text from a user-specified or default path for object_name.

    Side-effects:
      * Logging at info level, mentioning object_name and the path used
      * Copying either the user_path or default_path to cache_dir

    Return:
        Text of file content or empty string if neither path or default are specified
    """
    if user_path is None:
        if not default_path:
            return ""
        path = Path(default_path)
        logger.info("Cache default %s: '%s'", object_name, path.absolute())
    else:
        path = Path(user_path)
        logger.info("Cache user-specified %s: '%s'", object_name, path.absolute())
    dest = cache_dir / path.name
    shutil.copy(path, dest)
    return dest.read_text()


def cache_user_or_default_json(object_name, user_path, default_path, cache_dir):
    """
    Read JSON from a user-specified or default path for object_name.

    Side-effects:
      * Logging at info level, mentioning object_name and the path used
      * Copying either the user_path or default_path to cache_dir

    Return:
        Python objects
    """
    return json.loads(
        cache_user_or_default_text(
            object_name=object_name,
            user_path=user_path,
            default_path=default_path,
            cache_dir=cache_dir,
        )
    )


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
        help="Fetch repeaters within X distance of POIs defined in a CSV file",
    )
    parser.add_argument(
        "--repeaterbook-state",
        nargs="*",
        help="Download repeaters from the given state(s). Default: '{}'".format(
            "' '".join(dzcb.repeaterbook.REPEATERBOOK_DEFAULT_STATES),
        ),
    )
    parser.add_argument(
        "--repeaterbook-name-format",
        help=(
            "Python format string used to generate channel names from repeaterbook. "
            "See Repeaterbook API response for usable field names. Default: '{}'".format(
                dzcb.repeaterbook.REPEATERBOOK_DEFAULT_NAME_FORMAT,
            )
        ),
    )
    parser.add_argument(
        "--default-k7abd",
        action="store_true",
        help="Include bundled K7ABD input files (simplex + unlicensed)",
    )
    parser.add_argument(
        "--k7abd",
        nargs="*",
        help="Specify one or more local directories containing K7ABD CSV files",
    )
    parser.add_argument(
        "--farnsworth-template-json",
        nargs="*",
        help="JSON file to take Farnsworth settings from. If no json file, defaults will "
        "be used for each supported radio type.",
    )
    parser.add_argument(
        "--scanlists-json",
        default=None,
        help="JSON dict mapping scanlist name to list of channel names.",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        help="Specify one or more CSV files with object names to include",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        help="Specify one or more CSV files with object names to exclude",
    )
    parser.add_argument(
        "--order",
        nargs="*",
        help="Specify one or more CSV files with object order by name",
    )
    parser.add_argument(
        "--reverse-order",
        nargs="*",
        help="Specify one or more CSV files with object order by name (reverse)",
    )
    parser.add_argument(
        "--replacements",
        nargs="*",
        help="Specify one or more CSV files with object name replacements",
    )
    parser.add_argument("outdir", help="Write code plug files to this directory")
    args = parser.parse_args()

    outdir = append_dir_and_create(Path(args.outdir))
    dzcb.log.init_logging(log_path=outdir)
    logger.info("dzcb %s outdir='%s'", __version__, outdir)

    cache_dir = append_dir_and_create(outdir, "cache")
    logger.debug("Using cache_dir: '%s'", cache_dir)

    # get overall ordering objects first and raise any validation errors
    ordering = {}
    for oarg_name in ["include", "exclude", "order", "reverse_order"]:
        ordering[oarg_name] = dzcb.model.Ordering()
        for f in getattr(args, oarg_name) or tuple():
            ordering[oarg_name] += dzcb.model.Ordering.from_csv(
                cache_user_or_default_text(
                    object_name=oarg_name,
                    user_path=f,
                    default_path=None,
                    cache_dir=cache_dir,
                ).splitlines()
            )

    replacements = dzcb.model.Replacements()
    for f in args.replacements or tuple():
        replacements += dzcb.model.Replacements.from_csv(
            cache_user_or_default_text(
                object_name="replacements",
                user_path=f,
                default_path=None,
                cache_dir=cache_dir,
            ).splitlines()
        )

    # fetch data from the internet
    if args.repeaterbook_proximity_csv:
        dzcb.repeaterbook.zones_to_k7abd(
            input_csv=args.repeaterbook_proximity_csv,
            output_dir=cache_dir,
            states=args.repeaterbook_state
            or dzcb.repeaterbook.REPEATERBOOK_DEFAULT_STATES,
            name_format=args.repeaterbook_name_format,
        )

    if args.pnwdigital:
        dzcb.pnwdigital.cache_repeaters(cache_dir)

    if args.seattledmr:
        dzcb.seattledmr.cache_repeaters(cache_dir)

    if args.default_k7abd:
        default_k7abd_path = files(dzcb.data) / "k7abd"
        logger.info("Cache default k7abd zones from: '%s'", default_k7abd_path)
        shutil.copytree(default_k7abd_path, cache_dir, dirs_exist_ok=True)

    if args.k7abd:
        # copy any additional CSV directories into the cache_dir
        for abd_dir in args.k7abd:
            logger.info("Cache k7abd zones from: '%s'", abd_dir)
            shutil.copytree(abd_dir, cache_dir, dirs_exist_ok=True)

    # load additional data files or defaults
    scanlists = cache_user_or_default_json(
        object_name="scanlists",
        user_path=args.scanlists_json,
        default_path=files(dzcb.data).joinpath("scanlists.json"),
        cache_dir=cache_dir,
    )

    # create codeplug from a directory of k7abd CSVs
    cp = (
        dzcb.k7abd.Codeplug_from_k7abd(cache_dir)
        .filter(replacements=replacements, **ordering)
        .replace_scanlists(scanlists)
    )
    logger.info("Generated %s", cp)

    # GB3GF CSV - Radioddity GD77/OpenGD77, TYT MD-380, MD-9600, Baofeng DM1801, RD-5R
    # XXX: Only support OpenGD77 at the moment
    gb3gf_outdir = append_dir_and_create(outdir, "gb3gf")
    gd77_outdir = append_dir_and_create(gb3gf_outdir, "opengd77")
    dzcb.gb3gf.Codeplug_to_gb3gf_opengd77_csv(
        cp=cp,
        output_dir=gd77_outdir,
    )

    # The following models use expand_static_talkgroups to create
    # one channel per talkgroup / one zone per repeater
    fw_cp = (
        cp.expand_static_talkgroups()
        .filter(replacements=replacements, **ordering)
        .replace_scanlists(scanlists)
    )
    logger.info("Expand static talkgroups %s", fw_cp)

    # Anytone 578/868/878 stock CPS CSV import files
    anytone_outdir = append_dir_and_create(outdir, "anytone")
    dzcb.anytone.Codeplug_to_anytone_csv(
        cp=fw_cp,
        output_dir=anytone_outdir,
    )

    # Farnsworth JSON - TYT et. al w/ Zone Import!
    farnsworth_templates = []
    if args.farnsworth_template_json is None:
        # Iterate through all farnsworth templates, generating codeplug for each
        for f in (files(dzcb.data) / "farnsworth").iterdir():
            if not str(f).endswith(".json"):
                continue
            farnsworth_templates.append((f, f.name, f.open("r")))
    else:
        farnsworth_templates = [
            (ftj, os.path.basename(ftj), open(ftj, "r"))
            for ftj in args.farnsworth_template_json
        ]

    fw_outdir = append_dir_and_create(outdir, "editcp")
    for ftj, fname, fh in farnsworth_templates:
        outfile = fw_outdir / fname
        outfile.write_text(
            dzcb.farnsworth.Codeplug_to_json(
                cp=fw_cp,
                based_on=fh,
            )
        )
        logger.info("Wrote '%s' based JSON to '%s'", ftj, outfile)
