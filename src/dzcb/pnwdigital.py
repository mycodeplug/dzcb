"""
dzcb.pnwdigital - cache data from PNWDigital.net
"""
from pathlib import Path
import tempfile
from zipfile import ZipFile

import requests

PNWDIGITAL_REPEATERS = "http://www.pnwdigital.net/sv/PNW_Digital_Repeaters.zip"
REPEATER_FILENAME = "Digital-Repeaters__PNWDigital.csv"
TALKGROUPS_FILENAME = "Talkgroups__PNWDigital.csv"


def cache_repeaters(output_dir):
    resp = requests.get(PNWDIGITAL_REPEATERS)
    resp.raise_for_status()
    with tempfile.TemporaryFile() as tf:
        tf.write(resp.content)
        zf = ZipFile(tf, "r")
        names = zf.namelist()
        zip_repeater_filename = [
            n for n in names if n.startswith("Digital-Repeaters__PNW-all")
        ]
        if len(zip_repeater_filename) > 1:
            raise RuntimeError(
                "Multiple Digital-Repeaters found in the zip: {}".format(
                    zip_repeater_filename
                )
            )
        (Path(output_dir) / REPEATER_FILENAME).write_bytes(
            zf.read(zip_repeater_filename[0])
        )
        zip_talkgroups_filename = [
            n for n in names if n.startswith("Talkgroups__PNW-all")
        ]
        if len(zip_talkgroups_filename) > 1:
            raise RuntimeError(
                "Multiple Talkgroups found in the zip: {}".format(
                    zip_talkgroups_filename
                )
            )
        (Path(output_dir) / TALKGROUPS_FILENAME).write_bytes(
            zf.read(zip_talkgroups_filename[0])
        )
