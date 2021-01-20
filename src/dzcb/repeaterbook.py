"""
dzcb.repeaterbook - export CSV from Repeaterbook, convert to K7ABD format
"""
import argparse
import contextlib
import csv
import hashlib
import logging
from pathlib import Path
import os
import time

from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

REPEATERBOOK_INDEX = "https://www.repeaterbook.com/index.php"
REPEATERBOOK_LOGIN = (
    "https://www.repeaterbook.com/index.php/user-profile?task=user.login"
)
REPEATERBOOK_EXPORT = (
    "https://www.repeaterbook.com/repeaters/downloads/csv/index.php?"
    "func=prox&features%5B0%5D=FM&"
    "lat={lat}&long={lon}&"
    "distance={distance}&Dunit={dunit}&"
    "band1={band1}&band2={band2}&"
    "call=&use=OPEN&status_id=1&order=distance_calc,%20state_id,%20`call`%20ASC"
)


@contextlib.contextmanager
def text_login(username=None, password=None):
    """
    Login to Repeaterbook.com with the given credentials.

    The useful search/export functionalities require an authenticated user.

    :param username: Optional repeaterbook username.
        default: environment variable - REPEATERBOOK_USER
    :param password: Optional repeaterbook password.
        default: environment variable - REPEATERBOOK_PASSWD
    :return: requests.Session with logged in cookie
    """
    payload = {
        "username": username or os.environ["REPEATERBOOK_USER"],
        "password": password or os.environ["REPEATERBOOK_PASSWD"],
    }
    with requests.Session() as session:
        index = session.get(REPEATERBOOK_INDEX)
        index.raise_for_status
        soup = BeautifulSoup(index.text, features="html.parser")
        # have to find the CSRF token
        noncsrf_inputs = "remember", "username", "password"
        copy_inputs = "option", "task", "return"
        for inp in soup.form.find_all("input"):
            if inp.attrs["name"] in noncsrf_inputs:
                continue
            payload[inp.attrs["name"]] = inp.attrs["value"]

        login = session.post(REPEATERBOOK_LOGIN, data=payload)
        login.raise_for_status()
        session._username = payload["username"]
        yield session


def proximity_zones(proximity_zones_csv):
    csvr = csv.DictReader(
        proximity_zones_csv,
        fieldnames=["name", "lat", "lon", "distance", "dunit", "band1", "band2"],
    )
    for zone in csvr:
        zone = zone.copy()
        name = zone.pop("name")
        slug = name.replace(" ", "-").replace(",", "")
        url = REPEATERBOOK_EXPORT.format(**zone)
        md5urlhash = hashlib.md5(url.encode("utf-8")).hexdigest()
        filename = "{}_{}.csv".format(slug, md5urlhash)
        yield (name, slug, url, filename)


def cache_zones_with_proximity(input_csv, output_dir, delay=0.25):
    output_dir = Path(output_dir)
    zones = tuple(proximity_zones(input_csv))
    with text_login() as session:
        logger.info(
            "Downloading %s proximity zones as %s (%s seconds)",
            len(zones),
            session._username,
            len(zones) * delay,
        )
        for name, slug, url, filename in zones:
            resp = session.get(url)
            resp.raise_for_status()
            out_file = output_dir / filename
            out_file.write_text(resp.text)
            logger.debug("Cache raw CSV to '%s'", out_file)
            time.sleep(delay)


def zones_to_k7abd(input_csv, input_dir, output_dir):
    for name, slug, url, filename in proximity_zones(input_csv):
        in_file = Path(input_dir) / filename
        out_file = Path(output_dir) / "Analog__{}.csv".format(slug)
        with open(in_file, "r") as inp, open(out_file, "w", newline="") as out:
            csvr = csv.DictReader(inp)
            csvw = csv.DictWriter(
                out,
                fieldnames=[
                    "Zone",
                    "Channel Name",
                    "Bandwidth",
                    "Power",
                    "RX Freq",
                    "TX Freq",
                    "CTCSS Decode",
                    "CTCSS Encode",
                    "TX Prohibit",
                ],
            )
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
                csvw.writerow(
                    {
                        "Zone": name,
                        "Channel Name": "{} {}".format(row["Call"], row["Location"]),
                        "Bandwidth": "25K",
                        "Power": "High",
                        "RX Freq": str(freq),
                        "TX Freq": str(freq + offset),
                        "CTCSS Decode": row["Tone"] if row["Tone"] != "CSQ" else "Off",
                        "CTCSS Encode": row["Tone"] if row["Tone"] != "CSQ" else "Off",
                        "TX Prohibit": "Off",
                    }
                )
        logger.debug("Generate '%s' k7abd zones to '%s'", name, out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("proximity_csv_file", type=argparse.FileType("r"))
    parser.add_argument("output_dir")
    parser.add_argument("--cache-dir", default="/tmp/cache_dir")
    args = parser.parse_args()
    if not os.path.exists(args.cache_dir):
        os.makedirs(args.cache_dir)
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    proximity_csv = args.proximity_csv_file.read().splitlines()
    cache_zones_with_proximity(proximity_csv, args.cache_dir)
    zones_to_k7abd(proximity_csv, args.cache_dir, args.output_dir)
