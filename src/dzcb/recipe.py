"""
A recipe describes how to generate a codeplug
"""
from importlib_resources import files
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Union

import attr

from dzcb import __version__
import dzcb.anytone
import dzcb.data
import dzcb.farnsworth
import dzcb.gb3gf
import dzcb.log
import dzcb.model
import dzcb.output.dmrconfig
import dzcb.repeaterbook
import dzcb.pnwdigital
import dzcb.seattledmr


logger = logging.getLogger("dzcb.recipe")


# attr validator aliases
required_bool = attr.validators.instance_of(bool)
optional_bool = attr.validators.optional(required_bool)
str_or_Path = attr.validators.instance_of((str, Path))
optional_str_or_Path = attr.validators.optional(str_or_Path)
sequence_of_Path = attr.validators.optional(
    attr.validators.deep_iterable(member_validator=attr.validators.instance_of(Path))
)
sequence_of_str_or_path = attr.validators.optional(
    attr.validators.deep_iterable(
        member_validator=attr.validators.instance_of((str, Path))
    )
)


def maybe_path(obj: Any) -> Union[Any, Path]:
    """
    If the obj is a valid path that exists, return a Path
    """
    try:
        p = Path(obj)
    except Exception:
        pass
    else:
        if p.exists():
            return p
        else:
            # attempt to open the file to raise error
            p.open("r")
    return obj


def foreach_factory(func, optional=False, return_type=tuple):
    def _func_caller(objs):
        if optional and objs is None:
            return
        return return_type(func(obj) for obj in objs)

    return _func_caller


def Path_or_sequence_of_maybe_path(obj):
    obj = maybe_path(obj)
    if isinstance(obj, Path):
        return (obj,)
    return foreach_factory(maybe_path, optional=True)(obj)


def from_csv_or_Path(obj, from_csv_cls):
    # set the error before we overwrite obj
    error = "Cannot make an {} object from {!r}".format(from_csv_cls.__name__, obj)

    obj = maybe_path(obj)
    if isinstance(obj, (from_csv_cls, Path)):
        return obj

    try:
        if isinstance(obj, str):
            maybe_lines = obj.splitlines()
        else:
            maybe_lines = tuple(obj)  # cast tuple in case obj is a file-like
        return from_csv_cls.from_csv(maybe_lines)
    except Exception as e:  # TypeError not iterable or parse error
        raise ValueError(error) from e


def Ordering_or_Path(obj):
    return from_csv_or_Path(obj, from_csv_cls=dzcb.model.Ordering)


def to_sequence_of_Ordering_or_Path(obj):
    obj = maybe_path(obj)
    if isinstance(obj, (dzcb.model.Ordering, Path)):
        return (obj,)
    return foreach_factory(Ordering_or_Path, optional=True)(obj)


sequence_of_Ordering_or_Path = attr.validators.optional(
    attr.validators.deep_iterable(
        member_validator=attr.validators.instance_of((dzcb.model.Ordering, Path))
    )
)


def Replacements_or_Path(obj):
    return from_csv_or_Path(obj, from_csv_cls=dzcb.model.Replacements)


def to_sequence_of_Replacements_or_Path(obj):
    obj = maybe_path(obj)
    if isinstance(obj, (dzcb.model.Replacements, Path)):
        return (obj,)
    return foreach_factory(Replacements_or_Path, optional=True)(obj)


sequence_of_Replacements_or_Path = attr.validators.optional(
    attr.validators.deep_iterable(
        member_validator=attr.validators.instance_of((dzcb.model.Replacements, Path))
    )
)


def bool_or_sequence_of_maybe_path(obj):
    if isinstance(obj, bool):
        return obj
    obj = maybe_path(obj)
    if isinstance(obj, Path):
        return (obj,)
    return foreach_factory(maybe_path, optional=True)(obj)


def bool_or_sequence_of_Path(instance, attribute, value):
    if value in (None, True, False):
        return
    attr.validators.deep_iterable(member_validator=attr.validators.instance_of(Path))(
        instance, attribute, value
    )


def append_dir_and_create(path, *components):
    new_path = Path(path)
    if components:
        new_path = new_path / Path(*components)
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
        logger.info(
            "Cache %s%s: '%s'",
            "user-specified " if default_path else "",
            object_name,
            path.absolute(),
        )
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
    text = cache_user_or_default_text(
        object_name=object_name,
        user_path=user_path,
        default_path=default_path,
        cache_dir=cache_dir,
    )
    if text:
        return json.loads(text)


@attr.s
class CodeplugRecipe:
    """
    The input/manipulation/output of a codeplug.

    The CodeplugRecipe is instantiated by dzcb.__main__ (command line interface)
    or directly in any python script to fetch, update, and generate codeplugs for
    multiple output formats.

    First, all of the sources are processed, downloading and copying CSV files in the
    output "cache" directory.

    :param source_pnwdigital: True to download pnwdigital.net ACB files to cache dir
    :param source_seattledm: True to download seattledmr.org ACB files to cache dir
    :param source_default_k7abd: True to copy bundled k7abd simplex and hotspot pair files to cache dir
    :param source_k7abd: sequence of Path to directories containing k7abd CSV files to copy to cache dir
    :param source_repeaterbook_proximity: sequence of Path to repeaterbook proximity CSV files.
        Proximity CSV is used to create Analog k7abd zone files in the cache dir.
    :param repeaterbook_states: sequence of US State or Canadian Province to include in
        proximity search. Minimize this set to reduce generation time.
    :param repeaterbook_name_format: optional. format string for converting repeaterbook API dict to
        name in the k7abd output file.

    Note: source_k7abd and source_repeaterbook_proximity also accept a sequence of string
    (CSV with newlines)

    Next, the k7abd format CSV files are assembled into a dzcb.model.Codeplug
    and manipulations are applied as specified.

    :param scanlists_json: JSON string or Path to JSON file containing additional scanlists
        {"scanlist1": ["ch1", "ch2", ..., "chN"], "scanlist2": ["ch1", "ch2"], ..., "scanlistN": [...]}
    :param include: sequence of Ordering object or Path to ordering CSV file to be included
    :param exclude: sequence of Ordering object or Path to ordering CSV file to be excluded
    :param order: sequence of Ordering object or Path to ordering CSV file for ordering objects
    :param reverse_order: sequence of Ordering object or Path to ordering CSV file for reverse ordering objects
    :param replacements: sequence of Replacements object or Path to replacements CSV file

    Finally, the resulting codeplug is prepared for output to multiple formats. Additional
    filtering or expansion may occur at this point as well.

    :param output_anytone: if True, target the latest CPS version for each support radio.
        Otherwise a sequence of supported radio/CPS strings is expected:

            * "578_1_11"
            * "868_1_39"
            * "878_1_21"

    :param output_dmrconfig: if True, target all default dmrconfig templates.
        Otherwise a sequence of Path to dmrconfig template conf files is expected.
    :param output_farnsworth: if True, target all default editcp templates.
        Otherwise a sequence of Path to farnsworth template conf files is expected.
    :param output_gb3gf: if True, target OpenGD77 via GB3BF CSV import tool
        No other models are supported at this time.
    """

    # input control
    source_pnwdigital = attr.ib(default=False, validator=required_bool, converter=bool)
    source_seattledmr = attr.ib(default=False, validator=required_bool, converter=bool)
    source_default_k7abd = attr.ib(
        default=False, validator=required_bool, converter=bool
    )
    source_k7abd = attr.ib(
        default=None,
        validator=sequence_of_Path,
        converter=Path_or_sequence_of_maybe_path,
    )
    source_repeaterbook_proximity = attr.ib(
        default=None,
        validator=sequence_of_Path,
        converter=Path_or_sequence_of_maybe_path,
    )

    # manipulation
    scanlists_json = attr.ib(
        default=None, validator=optional_str_or_Path, converter=maybe_path
    )
    ordering_field = dict(
        validator=sequence_of_Ordering_or_Path,
        converter=to_sequence_of_Ordering_or_Path,
    )
    include = attr.ib(default=None, **ordering_field)
    exclude = attr.ib(default=None, **ordering_field)
    order = attr.ib(default=None, **ordering_field)
    reverse_order = attr.ib(default=None, **ordering_field)
    replacements = attr.ib(
        default=None,
        validator=sequence_of_Replacements_or_Path,
        converter=to_sequence_of_Replacements_or_Path,
    )

    # output control
    output_anytone = attr.ib(default=None)
    output_dmrconfig = attr.ib(
        default=None,
        validator=bool_or_sequence_of_Path,
        converter=bool_or_sequence_of_maybe_path,
    )
    output_farnsworth = attr.ib(
        default=None,
        validator=bool_or_sequence_of_Path,
        converter=bool_or_sequence_of_maybe_path,
    )
    output_gb3gf = attr.ib(default=None)

    # additional options
    repeaterbook_states = attr.ib(default=dzcb.repeaterbook.REPEATERBOOK_DEFAULT_STATES)
    repeaterbook_name_format = attr.ib(
        default=dzcb.repeaterbook.REPEATERBOOK_DEFAULT_NAME_FORMAT
    )

    # these are used during generation and cannot be initialized
    _output_dir = attr.ib(default=None, init=False)
    _cache_dir = attr.ib(default=None, init=False)
    _input_dir = attr.ib(default=None, init=False)
    _ordering = attr.ib(default=None, init=False)
    _replacements = attr.ib(default=None, init=False)
    _scanlists = attr.ib(default=None, init=False)
    _codeplug = attr.ib(default=None, init=False)
    _codeplug_expanded = attr.ib(default=None, init=False)

    @output_anytone.validator
    def _output_anytone_validator(self, attribute, value):
        if value in (None, True, False):
            return
        for rcps in value:
            if rcps not in dzcb.anytone.SUPPORTED_RADIOS:
                raise ValueError(
                    "{!r} is not a supported Radio/CPS version ({})".format(
                        rcps, ", ".join(dzcb.anytone.SUPPORTED_RADIOS.keys())
                    )
                )

    @output_gb3gf.validator
    def _output_gb3gf_validator(self, attribute, value):
        if value in (None, True, False):
            return
        for radio in value:
            if radio not in dzcb.gb3gf.SUPPORTED_RADIOS:
                raise ValueError(
                    "{!r} is not a supported Radio ({})".format(
                        radio, ", ".join(dzcb.gb3gf.SUPPORTED_RADIOS)
                    )
                )

    def initialize(self, output_dir):
        self._output_dir = append_dir_and_create(output_dir).resolve()
        dzcb.log.init_logging(log_path=self.output_dir)
        logger.info("dzcb %s output_dir='%s'", __version__, self.output_dir)
        self.init_ordering()
        self.init_replacements()
        self.init_scanlists()

    @property
    def output_dir(self):
        if self._output_dir is None:
            raise RuntimeError("output_dir is not set. call initialize()")
        return self._output_dir

    @property
    def cache_dir(self):
        if self._cache_dir is None:
            self._cache_dir = append_dir_and_create(self._output_dir, "cache")
            logger.debug(
                "Cache downloaded and generated files to: '%s'", self._cache_dir
            )
        return self._cache_dir

    @property
    def input_dir(self):
        if self._input_dir is None:
            self._input_dir = append_dir_and_create(self._output_dir, "input")
            logger.debug("Cache input files to: '%s'", self._input_dir)
        return self._input_dir

    def init_ordering(self):
        # get overall ordering objects first and raise any validation errors
        ordering = {}
        for oarg_name in ["include", "exclude", "order", "reverse_order"]:
            ordering[oarg_name] = dzcb.model.Ordering()
            for order_obj in getattr(self, oarg_name) or tuple():
                if not isinstance(order_obj, dzcb.model.Ordering):
                    order_obj = dzcb.model.Ordering.from_csv(
                        cache_user_or_default_text(
                            object_name=oarg_name,
                            user_path=order_obj,
                            default_path=None,
                            cache_dir=self.input_dir,
                        ).splitlines()
                    )
                ordering[oarg_name] += order_obj
        self._ordering = ordering

    def init_replacements(self):
        replacements = dzcb.model.Replacements()
        for rep_obj in self.replacements or tuple():
            if not isinstance(rep_obj, dzcb.model.Replacements):
                rep_obj = dzcb.model.Replacements.from_csv(
                    cache_user_or_default_text(
                        object_name="replacements",
                        user_path=rep_obj,
                        default_path=None,
                        cache_dir=self.input_dir,
                    ).splitlines()
                )
            replacements += rep_obj
        self._replacements = replacements

    def init_scanlists(self):
        try:
            # handle the case where it's a json string
            self._scanlists = json.loads(self.scanlists_json)
            return
        except TypeError:
            pass

        default_scanlists = None
        if self.source_default_k7abd:
            # the default scanlists go with the default analog zones
            default_scanlists = files(dzcb.data).joinpath("scanlists.json")
        self._scanlists = cache_user_or_default_json(
            object_name="scanlists",
            user_path=self.scanlists_json,
            default_path=default_scanlists,
            cache_dir=self.input_dir,
        )

    def repeaterbook_proximity(self):
        if not self.source_repeaterbook_proximity:
            return
        for src in self.source_repeaterbook_proximity:
            zone_csv = cache_user_or_default_text(
                "repeaterbook proximity csv",
                src,
                default_path=None,
                cache_dir=self.input_dir,
            )
            dzcb.repeaterbook.zones_to_k7abd(
                input_csv=zone_csv.splitlines(),
                output_dir=self.cache_dir,
                states=self.repeaterbook_states,
                name_format=self.repeaterbook_name_format,
            )

    def pnwdigital(self):
        if not self.source_pnwdigital:
            return
        dzcb.pnwdigital.cache_repeaters(self.cache_dir)

    def seattledmr(self):
        if not self.source_seattledmr:
            return
        dzcb.seattledmr.cache_repeaters(self.cache_dir)

    def default_k7abd(self):
        if not self.source_default_k7abd:
            return
        default_k7abd_path = files(dzcb.data) / "k7abd"
        logger.info("Cache default k7abd zones from: '%s'", default_k7abd_path)
        shutil.copytree(default_k7abd_path, self.cache_dir, dirs_exist_ok=True)

    def k7abd(self):
        if not self.source_k7abd:
            return
        for abd_dir in self.source_k7abd:
            logger.info("Cache k7abd zones from: '%s'", abd_dir)
            shutil.copytree(abd_dir, self.cache_dir, dirs_exist_ok=True)

    def source(self):
        self.repeaterbook_proximity()
        self.pnwdigital()
        self.seattledmr()
        self.default_k7abd()
        self.k7abd()

    def build_codeplug(self):
        self._codeplug = (
            dzcb.k7abd.Codeplug_from_k7abd(self.cache_dir)
            .filter(replacements=self._replacements, **self._ordering)
            .replace_scanlists(self._scanlists)
        )
        logger.info("Generated %s", self._codeplug)

    def expand_codeplug(self):
        self._codeplug_expanded = (
            self._codeplug.expand_static_talkgroups()
            .filter(replacements=self._replacements, **self._ordering)
            .replace_scanlists(self._scanlists)
        )
        logger.info("Expand static talkgroups %s", self._codeplug_expanded)

    def codeplug(self):
        self.build_codeplug()
        self.expand_codeplug()

    def anytone(self):
        if not self.output_anytone:
            return  # False or None, skip output
        if self.output_anytone is True:
            # default is "latest supported models"
            models = None
        else:
            models = self.output_anytone
        anytone_outdir = append_dir_and_create(self.output_dir, "anytone")
        dzcb.anytone.Codeplug_to_anytone_csv(
            cp=self._codeplug_expanded,
            output_dir=anytone_outdir,
            models=models,
        )

    @staticmethod
    def _templates_from_default(user_sequence, default_dir, suffix):
        if user_sequence is True:
            defaults = []
            # Iterate through all templates, generating codeplug for each
            for f in (files(dzcb.data) / default_dir).iterdir():
                if f.suffix != suffix:
                    continue
                defaults.append(f)
            return defaults
        return user_sequence

    def dmrconfig(self):
        if not self.output_dmrconfig:
            return
        dmrconfig_templates = self._templates_from_default(
            self.output_dmrconfig, "dmrconfig", ".conf"
        )

        dm_outdir = append_dir_and_create(self.output_dir, "dmrconfig")
        for dt in dmrconfig_templates:
            outfile = dm_outdir / dt.name
            outfile.write_text(
                dzcb.output.dmrconfig.Dmrconfig_Codeplug.from_codeplug(
                    self._codeplug_expanded,
                    template=cache_user_or_default_text(
                        "dmrconfig template",
                        dt,
                        default_path=None,
                        cache_dir=self.input_dir,
                    ),
                ).render_template()
            )
            logger.info("Wrote dmrconfig conf to '%s'", outfile)

    def farnsworth(self):
        if not self.output_farnsworth:
            return
        farnsworth_templates = self._templates_from_default(
            self.output_farnsworth, "farnsworth", ".json"
        )

        fw_outdir = append_dir_and_create(self.output_dir, "editcp")
        for ftj in farnsworth_templates:
            outfile = fw_outdir / ftj.name
            outfile.write_text(
                dzcb.farnsworth.Codeplug_to_json(
                    cp=self._codeplug_expanded,
                    based_on=cache_user_or_default_text(
                        "farnsworth template",
                        ftj,
                        default_path=None,
                        cache_dir=self.input_dir,
                    ),
                )
            )
            logger.info("Wrote editcp JSON to '%s'", outfile)

    def gb3gf(self):
        # GB3GF CSV - Radioddity GD77/OpenGD77, TYT MD-380, MD-9600, Baofeng DM1801, RD-5R
        # XXX: Only support OpenGD77 at the moment
        if not self.output_gb3gf:
            return  # False or None, skip output
        if self.output_gb3gf is True:
            # default is "latest supported models"
            radios = dzcb.gb3gf.DEFAULT_SUPPORTED_RADIOS
        else:
            radios = self.output_gb3gf
        for radio in radios:
            gb3gf_outdir = append_dir_and_create(self.output_dir, "gb3gf")
            if radio == "opengd77":
                opengd77_outdir = append_dir_and_create(gb3gf_outdir, "opengd77")
                dzcb.gb3gf.Codeplug_to_gb3gf_opengd77_csv(
                    cp=self._codeplug,
                    output_dir=opengd77_outdir,
                )

    def output(self):
        self.anytone()
        self.dmrconfig()
        self.farnsworth()
        self.gb3gf()

    def deinitialize(self):
        dzcb.log.deinit_logging()

    def generate(self, output_dir):
        self.initialize(output_dir=output_dir)
        self.source()
        self.codeplug()
        self.output()
        self.deinitialize()
