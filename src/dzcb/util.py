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
