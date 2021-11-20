import logging
import os


STR_TO_BOOL = {
    "false": False,
    "no": False,
    "off": False,
    "0": False,
    0: False,
    "true": True,
    "yes": True,
    "on": True,
    "1": True,
    1: True,
}


logger = logging.getLogger(__name__)


def getenv_bool(var_name, default=False):
    """
    Retrieve the given environment variable as a bool.

    Will use the text translation table STR_TO_BOOL to facilitate the conversion
    so that "yes"/"no" and "on"/"off" can also be used.
    """
    val = os.environ.get(var_name, None)
    if val is None:
        return default
    return STR_TO_BOOL[val.lower()]


def unique_name(name, existing_names, fmt="{} {}"):
    """
    Create a unique name by appending numbers.

    :param name: the base name that numbers are added to
    :param existing_names: container of names that are taken (prefer set or dict)
    :param fmt: how to format the new name, default "{} {}"
        expects 2 positional args in a new-style format string
    :return: a name based on `name` that doesn't exist in `existing_names`.
    """
    ix = 0
    maybe_unique_name = name
    while maybe_unique_name in existing_names:
        maybe_unique_name = fmt.format(name, ix)
        ix += 1
    if maybe_unique_name != name:
        logger.warning(
            "Deduping name {!r} -> {!r}. Consider using unique names for clarity.".format(
                name,
                maybe_unique_name,
            ),
        )
    return maybe_unique_name
