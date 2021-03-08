"""
dzcb main program

see dzcb.recipe for codeplug generation routines
"""

import argparse

import dzcb.recipe
import dzcb.repeaterbook


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
        "--dmrconfig-template",
        nargs="*",
        help="dmrconfig template files with codeplug objects removed. If no template is"
        "specified, the default 868 template will be used.",
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
        output_anytone=True,
        output_dmrconfig=args.dmrconfig_template or True,
        output_farnsworth=args.farnsworth_template_json or True,
        output_gb3gf=True,
    ).generate(output_dir=args.outdir)
