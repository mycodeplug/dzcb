"""
Convert repeaterbook CSV exports to K7ABD format Analog__
zone files.
"""
import contextlib
import csv
import hashlib
from importlib_resources import files
import os
import sys
import time

from bs4 import BeautifulSoup
import requests

from . import data

REPEATERBOOK_EXPORT = "https://www.repeaterbook.com/repeaters/downloads/csv/index.php?func=proxX&features%5B0%5D=FM&lat={lat}&long={lon}&distance={distance}&Dunit={dunit}&band1={band1}&band2={band2}&call=&use=OPEN&status_id=1&order=distance_calc,%20`call`%20ASC"
RPB = lambda p: os.path.join(os.path.dirname(data.__file__), "repeaterbook", p)
ABD = lambda p: os.path.join(os.path.dirname(data.__file__), "k7abd", p)

raw_zones = files(data).joinpath("repeaterbook_zones.csv").read_text().splitlines()
csvr = csv.DictReader(raw_zones, fieldnames=["name", "lat", "lon", "distance", "dunit", "band1", "band2"])
for zone in list(csvr):
    zone = zone.copy()
    name = zone.pop("name")
    slug = name.replace(" ", "-").replace(",", "")
    url = REPEATERBOOK_EXPORT.format(**zone)
    md5urlhash = hashlib.md5(url.encode("utf-8")).hexdigest()
    in_file = RPB("{}_{}.csv".format(slug, md5urlhash))
    out_file = ABD("Analog__{}.csv".format(slug))
    with open(in_file, "r") as inp, open(out_file, "w") as out:
        csvr = csv.DictReader(inp)
        csvw = csv.DictWriter(out, fieldnames=["Zone", "Channel Name", "Bandwidth", "Power", "RX Freq", "TX Freq", "CTCSS Decode", "CTCSS Encode", "TX Prohibit"])
        csvw.writeheader()
        # XXX: the unit is part of the field name..? groan
        #      this will break if the user changes from m to km
        for row in sorted(csvr, key=lambda r: float(r["Miles"])):
            freq = float(row["Freq"][:-1])
            offsetdir = row["Freq"][-1]
            if 144 <= freq <= 148:
                offset = 0.6
            elif 430 <= freq <= 460:
                offset = 5
            if offsetdir == "-":
                offset = -offset
            csvw.writerow({
                "Zone": name,
                "Channel Name": "{} {}".format(row["Call"], row["Location"])[:16],
                "Bandwidth": "25K",
                "Power": "High",
                "RX Freq": str(freq),
                "TX Freq": str(freq + offset),
                "CTCSS Decode": row["Tone"] if row["Tone"] != "CSQ" else "Off",
                "CTCSS Encode": row["Tone"] if row["Tone"] != "CSQ" else "Off",
                "TX Prohibit": "Off"
            })
