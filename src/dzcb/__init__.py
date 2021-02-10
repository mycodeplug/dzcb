"""
dzcb: DMR Zone Channel Builder

Fetch - fetch input files from local directories or urls
Assemble - combine information from multiple sources
Filter - rename, exclude, reorder zones, and talkgroups
Format - output to common export formats
"""
import enum

import appdirs
from pkg_resources import get_distribution

__version__ = get_distribution(__name__).version
__minor_version__ = ".".join(__version__.split(".")[:2])

COMMERCIAL_VHF = (136.0, 174.0)
COMMERCIAL_UHF = (400.0, 480.0)
AMATEUR_220 = (222.0, 225.0)


class AmateurBands(enum.Enum):
    B_10m = (28.0, 29.7)
    B_6m = (50.0, 54.0)
    B_2m = (144.0, 148.0)
    B_125cm = (222.0, 225.0)
    B_70cm = (420.0, 450.0)
    B_33cm = (902.0, 928.0)
    B_23cm = (1240.0, 1300.0)

    @classmethod
    def get_normalized(cls, input):
        if str(input).startswith("B_"):
            return getattr(cls, str(input))
        all_bands = cls.__members__
        maybe_band = "B_" + str(input)
        if maybe_band in all_bands:
            return getattr(cls, maybe_band)
        if str(input).lower() in ("1.25m", "220"):
            return cls.B_125cm
        try:
            input = float(input)
        except ValueError:
            pass
        if isinstance(input, (int, float)):
            # return the band that the frequency is from
            for band in all_bands.values():
                f_low, f_high = band.value
                if f_low <= input <= f_high:
                    return band
        raise ValueError(
            "Unknown amateur band/frequency: {!r}\nChoose from {!r}".format(
                input, list(all_bands.values())
            ),
        )


appdir = appdirs.AppDirs("dzcb", "mycodeplug", version=__minor_version__)
