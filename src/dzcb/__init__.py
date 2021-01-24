"""
dzcb: DMR Zone Channel Builder

Fetch - fetch input files from local directories or urls
Assemble - combine information from multiple sources
Filter - rename, exclude, reorder zones, and talkgroups
Format - output to common export formats
"""

from pkg_resources import get_distribution

__version__ = get_distribution(__name__).version

COMMERCIAL_VHF = (136.0, 174.0)
COMMERCIAL_UHF = (400.0, 480.0)
AMATEUR_220 = (222.0, 225.0)
