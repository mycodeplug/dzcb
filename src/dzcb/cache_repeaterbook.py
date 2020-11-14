"""
Cache repeaterbook CSV files
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

REPEATERBOOK_INDEX = "https://www.repeaterbook.com/index.php"
REPEATERBOOK_LOGIN = "https://www.repeaterbook.com/index.php/user-profile?task=user.login"
REPEATERBOOK_EXPORT = "https://www.repeaterbook.com/repeaters/downloads/csv/index.php?func=proxX&features%5B0%5D=FM&lat={lat}&long={lon}&distance={distance}&Dunit={dunit}&band1={band1}&band2={band2}&call=&use=OPEN&status_id=1&order=distance_calc,%20`call`%20ASC"

BASE = lambda p: os.path.join(os.path.dirname(data.__file__), "repeaterbook", p)

@contextlib.contextmanager
def repeaterbook_session(username=None, password=None):
    payload = {
        "username": username or os.environ["REPEATERBOOK_USER"],
        "password": password or os.environ["REPEATERBOOK_PASSWD"]
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
        yield session


raw_zones = files(data).joinpath("repeaterbook_zones.csv").read_text().splitlines()
csvr = csv.DictReader(raw_zones, fieldnames=["name", "lat", "lon", "distance", "dunit", "band1", "band2"])
zones = list(csvr)
with repeaterbook_session() as session:
    for zone in zones:
        zone = zone.copy()
        name = zone.pop("name")
        slug = name.replace(" ", "-").replace(",", "")
        url = REPEATERBOOK_EXPORT.format(**zone)
        md5urlhash = hashlib.md5(url.encode("utf-8")).hexdigest()
        resp = session.get(url)
        resp.raise_for_status()
        with open(BASE("{}_{}.csv".format(slug, md5urlhash)), "w") as f:
            f.write(resp.text)
        sys.stderr.write(".")
        time.sleep(0.25)
