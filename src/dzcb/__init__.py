"""
dzcb - DMR Zone Channel Builder

Automatically build digital channels from zone descriptions.
"""
import csv
import enum
from importlib_resources import files
import logging

import attr
from bs4 import BeautifulSoup
import requests

# cached data for testing
import dzcb.data

def read_shortcodes(filename="pnwdigital_site_shortcode.csv"):

    def parse_line(line):
        site_id, shortcode = line.strip().split(",", 2)
        return int(site_id), shortcode
    
    return dict(
        parse_line(l) for l in files(dzcb.data).joinpath(
            filename
        ).read_text().splitlines()
    )


PNWDIGITAL_REPEATERS = "http://pnwdigital.net/repeaters.html"
PNWDIGITAL_REPEATERS_CACHED = files(dzcb.data).joinpath("pnwdigital", "repeaters.html")
PNWDIGITAL_SHORTCODES = read_shortcodes()
PNWDIGITAL_SITES = "http://pnwdigital.net/sv/tgquery.php"
PNWDIGITAL_SITES_CACHED = files(dzcb.data).joinpath("pnwdigital", "tgquery.html")
PNWDIGITAL_TGQ = "http://pnwdigital.net/sv/tgshow3.php"
PNWDIGITAL_TGQ_CACHED = lambda site_id: files(dzcb.data).joinpath("pnwdigital", "{}.html".format(site_id))
REPEATERBOOK_EXPORT = "https://www.repeaterbook.com/repeaters/downloads/csv/index.php?func=proxX&features%5B0%5D=FM&lat=46.13819885&long=-122.93800354&distance=50&Dunit=m&band1=14&band2=4&call=&use=OPEN&status_id=1&order=distance_calc,%20state_id,%20`call`%20ASC"


@attr.s
class DigitalRepeater:
    name = attr.ib()
    code = attr.ib()
    state = attr.ib()
    city = attr.ib()
    frequency = attr.ib()
    offset = attr.ib()
    color_code = attr.ib()
    _site_id = attr.ib()
    talkgroups = attr.ib(factory=list)

    @classmethod
    def from_option_tag(cls, o):
        dr = cls(name=None, code=None, city=o.string.strip(), state=None, frequency=None, offset=None, color_code=None, site_id=int(o["value"].strip()))
        # XXX: read from cache for testing
        dr.populate_talkgroups_from_html(PNWDIGITAL_TGQ_CACHED(dr._site_id).read_text())
        return dr

    @classmethod
    def from_html(cls, html):
        soup = BeautifulSoup(html, features="html.parser")
        return [
            DigitalRepeater.from_option_tag(o)
            for o in soup.form.find_all("option")
            if o["value"] != "0"
        ]

    @classmethod
    def from_cache_all(cls):
        return cls.from_html(PNWDIGITAL_SITES_CACHED.read_text())

    def download_talkgroup_html(self):
        return requests.get(PNWDIGITAL_TGQ, params={"site": self._site_id})

    def populate_talkgroups_from_html(self, html):
        soup = BeautifulSoup(html, features="html.parser")
        outer_rows = soup.table.find_all("tr")
        self.name = outer_rows[0].find_all("font")[0].string.strip().replace(" Talk Group Deck", "")
        talkgroups = []
        for tg_row in outer_rows[1].table.find_all("tr")[1:]:
            try:
                tg = Talkgroup.from_table_row(tg_row)
            except Exception:
                logging.exception("Ignored")
                continue
            talkgroups.append(tg)
        self.talkgroups = talkgroups
        return self


class InvalidDmrID(ValueError):
    pass


class Timeslot(enum.Enum):
    ONE = 1
    TWO = 2

    def __repr__(self):
        return str(self.value)


@attr.s(eq=True)
class Contact:
    name = attr.ib(eq=True)
    dmr_id = attr.ib(eq=True, order=True)


@attr.s(eq=True)
class Talkgroup(Contact):
    timeslot = attr.ib(eq=True, order=True)

    all_talkgroups_by_id = {}

    @property
    def name_with_timeslot(self):
        ts = str(self.timeslot.value)
        if self.name.endswith(ts) and not self.name.startswith("TAC"):
            return self.name
        return "{} {}".format(self.name, ts)

    @classmethod
    def from_table_row(cls, tr):
        td_name, td_id, td_ts = tr.find_all("td")[:3]
        tg_name = td_name.string.strip()
        try:
            tg_id = int(td_id.string.strip())
        except ValueError as exc:
            raise InvalidDmrID("{}: {} is not numeric".format(tg_name, td_id.string)) from exc
        if tg_id <= 0:
            raise InvalidDmrID("{}: {} <= 0".format(tg_name, tg_id))
        tg_ts = Timeslot(int(td_ts.string.strip()))
        tg = cls(name=tg_name, dmr_id=tg_id, timeslot=tg_ts)

        # Find incongruencies with the same TG ID
        existing_tg = cls.all_talkgroups_by_id.get(tg_id)
        if existing_tg is not None and existing_tg != tg:
            raise RuntimeError("Already seen ID {}, but {!r} != {!r}".format(tg_id, existing_tg, tg))
        if existing_tg is None:
            cls.all_talkgroups_by_id[tg_id] = tg
        # Always return the cached copy
        return cls.all_talkgroups_by_id[tg_id]


@attr.s
class Channel:
    repeater = attr.ib()
    talkgroup = attr.ib()
    timeslot = attr.ib()
    rx_list = attr.ib()


def pnwdigital_query_repeaters():
    return requests.get(PNWDIGITAL_REPEATERS)


def pnwdigital_query_sites():
    return requests.get(PNWDIGITAL_SITES)


def write_talkgroup_matrix(repeaters, fh):
    headers = ["Zone Name", "Comment", "Power", "RX Freq", "TX Freq", "Color Code"]
    headers.extend(sorted(tg.name_with_timeslot for tg in Talkgroup.all_talkgroups_by_id.values()))
    dw = csv.DictWriter(fh, headers, restval="-")
    dw.writeheader()
    for r in repeaters:
        rdict = {
            "Zone Name": "{} {} {}".format(r.city, r.name, r._site_id),
            "Comment": "",
            "Power": "high",
            "RX Freq": "??",
            "TX Freq": "??",
            "Color Code": "1",
        }
        for tg in r.talkgroups:
            rdict[tg.name_with_timeslot] = str(tg.timeslot.value)
        dw.writerow(rdict)
