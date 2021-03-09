"""
dzcb main program

see dzcb.recipe for codeplug generation routines
"""

import argparse

import dzcb.anytone
import dzcb.gb3gf
import dzcb.recipe
import dzcb.repeaterbook


def is_specified(arg):
    if arg is not None and not arg:
        return True
    return arg


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
        "--repeaterbook-proximity-csv",
        nargs="*",
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
    parser.add_argument(
        "--anytone",
        nargs="*",
        help="Anytone radio+CPS versions to use when creating anytone CSV. "
        "One codeplug per radio+CPS version specified will be generated in the 'anytone' "
        "subdir of the output directory. If no radio+CPS versions are given use "
        "default versions: ({})".format(
            ", ".join(dzcb.anytone.DEFAULT_SUPPORTED_RADIOS)
        ),
    )
    parser.add_argument(
        "--dmrconfig-template",
        "--dmrconfig",
        nargs="*",
        help="dmrconfig conf file(s) to use when creating dmrconfig codeplugs. "
        "One codeplug per file specified will be generated in the 'dmrconfig' "
        "subdir of the output directory. If no files are given, use "
        "default template files",
    )
    parser.add_argument(
        "--farnsworth-template-json",
        "--farnsworth-template",
        "--farnsworth",
        "--editcp",
        nargs="*",
        help="JSON file(s) to use when creating farnsworth editcp codeplugs. "
        "One codeplug per file specified will be generated in the 'editcp' "
        "subfolder of the output directory. If no files are given, use the"
        "default template files",
    )
    parser.add_argument(
        "--gb3gf",
        nargs="*",
        help="Radio types to use when creating gb3gf CSV files. "
        "One codeplug per radio type specified will be generated in the 'gb3gf' "
        "subdir of the output directory. If no radio types are given use "
        "default: ({})".format(", ".join(dzcb.gb3gf.DEFAULT_SUPPORTED_RADIOS)),
    )
    parser.add_argument("outdir", help="Write code plug files to this directory")
    args = parser.parse_args()

    dzcb.recipe.CodeplugRecipe(
        source_pnwdigital=args.pnwdigital,
        source_seattledmr=args.seattledmr,
        source_default_k7abd=args.default_k7abd,
        source_k7abd=args.k7abd,
        source_repeaterbook_proximity=args.repeaterbook_proximity_csv,
        repeaterbook_states=args.repeaterbook_state,
        repeaterbook_name_format=args.repeaterbook_name_format,
        scanlists_json=args.scanlists_json,
        include=args.include,
        exclude=args.exclude,
        order=args.order,
        reverse_order=args.reverse_order,
        replacements=args.replacements,
        output_anytone=is_specified(args.anytone),
        output_dmrconfig=is_specified(args.dmrconfig_template),
        output_farnsworth=is_specified(args.farnsworth_template_json),
        output_gb3gf=is_specified(args.gb3gf),
    ).generate(output_dir=args.outdir)
