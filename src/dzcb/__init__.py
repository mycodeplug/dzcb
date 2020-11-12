"""
dzcb - DMR Zone Channel Builder

Automatically build digital channels from zone descriptions.
"""
import csv
import enum
import json
from importlib_resources import files
import logging
import re

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
        parse_line(l)
        for l in files(dzcb.data).joinpath(filename).read_text().splitlines()
    )


NAME_MAX = 16
PNWDIGITAL_REPEATER_INFO_REX = re.compile(r"([0-9.]+).*([+-])([0-9.]+).*Mhz.*CC([0-9])")

PNWDIGITAL_REPEATERS = "http://pnwdigital.net/repeaters.html"
PNWDIGITAL_REPEATERS_CACHED = files(dzcb.data).joinpath("pnwdigital", "repeaters.html")
PNWDIGITAL_SHORTCODES = read_shortcodes()
PNWDIGITAL_SITES = "http://pnwdigital.net/sv/tgquery.php"
PNWDIGITAL_SITES_CACHED = files(dzcb.data).joinpath("pnwdigital", "tgquery.html")
PNWDIGITAL_TGQ = "http://pnwdigital.net/sv/tgshow3.php"
PNWDIGITAL_TGQ_CACHED = lambda site_id: files(dzcb.data).joinpath(
    "pnwdigital", "{}.html".format(site_id)
)
REPEATERBOOK_EXPORT = "https://www.repeaterbook.com/repeaters/downloads/csv/index.php?func=proxX&features%5B0%5D=FM&lat=46.13819885&long=-122.93800354&distance=50&Dunit=m&band1=14&band2=4&call=&use=OPEN&status_id=1&order=distance_calc,%20state_id,%20`call`%20ASC"
PNWDIGITAL_REPEATER_EXCLUDE = ["900"]


def wordset(dr):
    s = set(
        w.lower()
        for w in dr.name.split() + dr.city.split("/") + dr.city.split() + [dr.state]
        if w
    )
    if "heights" in s:
        s.add("hts")
    if "columbia" in s:
        s.add("columb")
    if "westhills" in s:
        s.add("west")
        s.add("hills")
    if "mountain" in s:
        s.add("mtn")
    if "e" in s:
        s.add("east")
    if "megler" in s:
        s.add("chinook")
    if "s." in s:
        s.add("south")
    if "ruston" in s:
        s.add("tacoma")
        s.add("nor")
    if "point" in s:
        s.add("pt")
    return s


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
    talkgroups = attr.ib(factory=list, repr=False)

    @classmethod
    def from_option_tag(cls, o):
        dr = cls(
            name=None,
            code=None,
            city=o.string.strip(),
            state=None,
            frequency=None,
            offset=None,
            color_code=None,
            site_id=int(o["value"].strip()),
        )
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
    def from_table_row(cls, tr):
        state, city_location, description, info = tr.find_all("td")[:4]
        city, _, location = (
            city_location.text.strip()
            .replace("\n", "")
            .replace("\t", "")
            .replace("\xa0", "")
            .rpartition("-")
        )
        city = city.strip()
        location = location.strip()
        info_raw = info.text.strip().replace("\n", "")
        info_match = PNWDIGITAL_REPEATER_INFO_REX.search(info_raw)
        if not info_match:
            raise RuntimeError("Cannot make sense of {!r}".format(info_raw))
        dr = cls(
            name=location,
            code=None,
            city=city,
            state=state.text.strip(),
            frequency=float(info_match.group(1)),
            offset=float(info_match.group(2) + info_match.group(3)),
            color_code=info_match.group(4),
            site_id=None,
        )
        return dr

    @classmethod
    def from_repeaters_html(cls, html):
        """
        Parse /repeaters.html for:
          State, City, Location, Frequency, Color Code
        """
        soup = BeautifulSoup(html, features="html.parser")
        return [
            DigitalRepeater.from_table_row(tr) for tr in soup.table.find_all("tr")[1:-2]
        ]

    @classmethod
    def from_cache_all(cls):
        repeaters = cls.from_repeaters_html(PNWDIGITAL_REPEATERS_CACHED.read_text())
        sites = cls.from_html(PNWDIGITAL_SITES_CACHED.read_text())
        repeater_names = tuple((wordset(r), r) for r in repeaters)
        best_match = {}
        for s in sites:
            if s.name in PNWDIGITAL_REPEATER_EXCLUDE:
                print("Ignoring {}: in exclude list".format(s.name))
                continue
            # silly matching algorithm to correlate names
            s_name = wordset(s)
            words_in_common = (0, None)
            for r_name, r in repeater_names:
                common = len(s_name.intersection(r_name))
                if common > words_in_common[0]:
                    words_in_common = (common, r)
            match = words_in_common[1]
            if match is None:
                print("{} doesn't match".format(s.name))
                continue
            if (
                match.name in best_match
                and best_match[match.name][0] >= words_in_common[0]
            ):
                print("{} isn't the best match".format(s.name))
                continue
            if match.name in PNWDIGITAL_REPEATER_EXCLUDE:
                print("Excluding {} from exclude list".format(match.name))
                continue
            best_match[match.name] = (words_in_common[0], words_in_common[1], s)
            print("Matched {} {} to {}".format(s.name, s.city, match.name))
        repeaters = []
        for _, r, s in best_match.values():
            r.talkgroups = s.talkgroups
            r._site_id = s._site_id
            r.code = PNWDIGITAL_SHORTCODES.get(r._site_id, "UNKNOWN")
            repeaters.append(r)
        return repeaters

    def download_talkgroup_html(self):
        return requests.get(PNWDIGITAL_TGQ, params={"site": self._site_id})

    def populate_talkgroups_from_html(self, html):
        soup = BeautifulSoup(html, features="html.parser")
        outer_rows = soup.table.find_all("tr")
        self.name = (
            outer_rows[0]
            .find_all("font")[0]
            .string.strip()
            .replace(" Talk Group Deck", "")
        )
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

    name_replacements = {
        "Longview/Kelso ": "",  # Duplicate city, name is more helpful
        "Arial Ariel": "Ariel",  # City and Name are "identical"
        "Bellevue/Seattle": "Bellevue",
        "Bellingham": "Bham",
        "Ellensburg": "Eberg",
        "Issaquah/Seattle": "SEA E.Tiger",
        "Portland": "PDX",
        "Seattle": "SEA",
    }

    @property
    def zone_name(self):
        name = "{} {} {}".format(self.code, self.city, self.name)
        # shorten names for channel display
        for old, new in self.name_replacements.items():
            name = name.replace(old, new)
        return name


class InvalidDmrID(ValueError):
    pass


class Timeslot(enum.Enum):
    ONE = 1
    TWO = 2

    def __repr__(self):
        return str(self.value)


@attr.s(eq=True, frozen=True)
class Contact:
    Name = attr.ib(eq=True)
    CallID = attr.ib(eq=True, order=True)
    CallReceiveTone = attr.ib(default=False)
    CallType = attr.ib(eq=True, default="Group")

    value_replacements = {
        None: "None",
        False: "No",
        True: "Yes",
    }

    def to_dict(self):
        return {
            k: self.value_replacements.get(v, str(v))
            for k, v in attr.asdict(self).items()
            if k in attr.fields_dict(Contact)
        }


@attr.s(eq=True, frozen=True)
class Talkgroup(Contact):
    timeslot = attr.ib(default=1, eq=True, order=True)
    # These are used when generating channel names
    name_replacements = {
        "Audio Test": "A.Test",
        "California": "CA",
        "English": "Eng",
        "Hawaii": "HI",
        "Idaho": "ID",
        "Montana": "MT",
        "North America": "NA",
        "Oregon": "OR",
        "Utah": "UT",
        "Washington": "WA",
        "Worldwide": "WW",
    }

    all_talkgroups_by_id = {}

    @property
    def name_with_timeslot(self):
        ts = str(self.timeslot.value)
        if self.Name.endswith(ts) and not self.Name.startswith("TAC"):
            name = self.Name
        else:
            name = "{} {}".format(self.Name, ts)
        # shorten names for channel display
        for old, new in self.name_replacements.items():
            name = name.replace(old, new)
        return name

    @classmethod
    def from_table_row(cls, tr):
        td_name, td_id, td_ts = tr.find_all("td")[:3]
        tg_name = td_name.string.strip()
        try:
            tg_id = int(td_id.string.strip())
        except ValueError as exc:
            raise InvalidDmrID(
                "{}: {} is not numeric".format(tg_name, td_id.string)
            ) from exc
        if tg_id <= 0:
            raise InvalidDmrID("{}: {} <= 0".format(tg_name, tg_id))
        tg_ts = Timeslot(int(td_ts.string.strip()))
        tg = cls(Name=tg_name, CallID=tg_id, timeslot=tg_ts)

        # Find incongruencies with the same TG ID
        existing_tg = cls.all_talkgroups_by_id.get(tg_id)
        if existing_tg is not None and existing_tg != tg:
            raise RuntimeError(
                "Already seen ID {}, but {!r} != {!r}".format(tg_id, existing_tg, tg)
            )
        if existing_tg is None:
            cls.all_talkgroups_by_id[tg_id] = tg
        # Always return the cached copy
        return cls.all_talkgroups_by_id[tg_id]


@attr.s
class GroupList:
    Name = attr.ib()
    Contact = attr.ib(factory=list)


@attr.s
class ScanList:
    Name = attr.ib()
    Channel = attr.ib(factory=list)
    PriorityChannel1 = attr.ib(default="Selected")
    PriorityChannel2 = attr.ib(default="Selected")
    PrioritySampleTime = attr.ib(default="750")
    SignallingHoldTime = attr.ib(default="500")
    TxDesignatedChannel = attr.ib(default="Selected")


@attr.s
class Channel:
    Name = attr.ib()
    ContactName = attr.ib()
    RxFrequency = attr.ib()
    TxFrequencyOffset = attr.ib()

    # defaults
    AdmitCriteria = attr.ib(default="Color code")
    AllowTalkaround = attr.ib(default=True)
    Autoscan = attr.ib(default=False)
    ChannelMode = attr.ib(default="Digital")
    Bandwidth = attr.ib()  # default depends on ChannelMode
    ColorCode = attr.ib(default=1)
    CtcssDecode = attr.ib(default=None)
    CtcssEncode = attr.ib(default=None)
    DCDMSwitch = attr.ib(default=False)
    DataCallConfirmed = attr.ib(default=False)
    Decode1 = attr.ib(default=False)
    Decode2 = attr.ib(default=False)
    Decode3 = attr.ib(default=False)
    Decode4 = attr.ib(default=False)
    Decode5 = attr.ib(default=False)
    Decode6 = attr.ib(default=False)
    Decode7 = attr.ib(default=False)
    Decode8 = attr.ib(default=False)
    DisplayPTTID = attr.ib(default=False)
    EmergencyAlarmAck = attr.ib(default=False)
    EmergencySystem = attr.ib(default=None)
    GPSSystem = attr.ib(default=None)
    GroupList = attr.ib(default=None)
    InCallCriteria = attr.ib(default="Follow Admit Criteria")
    LeaderMS = attr.ib(default=False)
    LoneWorker = attr.ib(default=False)
    Power = attr.ib(default="High")
    Privacy = attr.ib(default=None)
    PrivacyNumber = attr.ib(default=1)
    PrivateCallConfirmed = attr.ib(default=False)
    QtReverse = attr.ib(default=180)
    ReceiveGPSInfo = attr.ib(default=False)
    RepeaterSlot = attr.ib(default=1)
    ReverseBurst = attr.ib(default=False)
    RxOnly = attr.ib(default=False)
    RxRefFrequency = attr.ib(default="Medium")
    RxSignallingSystem = attr.ib(default=False)
    ScanList = attr.ib(default=None)
    SendGPSInfo = attr.ib(default=False)
    Squelch = attr.ib(default=0)
    Talkaround = attr.ib(default=False)
    Tot = attr.ib(default=90)
    TotRekeyDelay = attr.ib(default=0)
    TxRefFrequency = attr.ib(default="Medium")
    TxSignallingSystem = attr.ib(default=False)
    Vox = attr.ib(default=False)

    value_replacements = {None: "None", False: "Off", True: "On"}

    @Bandwidth.default
    def _Bandwidth_default(self):
        if self.ChannelMode == "Digital":
            return 12.5
        else:
            return 25

    @classmethod
    def from_repeater(cls, repeater):
        return [
            cls(
                Name="{} {}".format(tg.name_with_timeslot[:NAME_MAX-4], repeater.code[:3]),
                ContactName=tg.Name,
                RxFrequency=str(repeater.frequency),
                TxFrequencyOffset=str(repeater.offset),
                ColorCode=repeater.color_code,
                RepeaterSlot=tg.timeslot.value,
                GroupList="{} TS {}".format(repeater.code, tg.timeslot.value),
                ScanList=repeater.zone_name[:NAME_MAX],
            )
            for tg in repeater.talkgroups
        ]

    def to_dict(self):
        return {
            k: self.value_replacements.get(v, str(v))
            for k, v in attr.asdict(self).items()
        }


@attr.s
class Zone:
    Name = attr.ib()
    ChannelA = attr.ib(factory=list)
    ChannelB = attr.ib(factory=list)


@attr.s
class Codeplug:
    contacts = attr.ib(factory=list)
    channels = attr.ib(factory=list)
    grouplists = attr.ib(factory=list)
    scanlists = attr.ib(factory=list)
    zones = attr.ib(factory=list)

    @classmethod
    def from_repeaters(cls, repeaters):
        contacts = set()
        channels = list()
        grouplists = list()
        scanlists = list()
        zones = list()
        for r in repeaters:
            contacts.update(r.talkgroups)
            zone_channels = Channel.from_repeater(r)
            channels.extend(zone_channels)
            channel_names_1 = [
                c.Name
                for c in sorted(zone_channels, key=lambda c: c.Name)
                if c.RepeaterSlot == 1
            ]
            channel_names_2 = [
                c.Name
                for c in sorted(zone_channels, key=lambda c: c.Name)
                if c.RepeaterSlot == 2
            ]
            grouplists.append(
                GroupList(
                    Name="{} TS 1".format(r.code),
                    Contact=[
                        tg.Name for tg in r.talkgroups if tg.timeslot == Timeslot.ONE
                    ],
                )
            )
            grouplists.append(
                GroupList(
                    Name="{} TS 2".format(r.code),
                    Contact=[
                        tg.Name for tg in r.talkgroups if tg.timeslot == Timeslot.TWO
                    ],
                )
            )
            scanlists.append(
                ScanList(
                    Name=r.zone_name[:NAME_MAX],
                    Channel=channel_names_1 + channel_names_2,
                )
            )
            zones.append(
                Zone(
                    Name=r.zone_name[:NAME_MAX],
                    ChannelA=channel_names_1 + channel_names_2,
                    ChannelB=channel_names_2 + channel_names_1,
                )
            )
        return cls(
            contacts=sorted(list(contacts), key=lambda c: c.Name),
            channels=channels,
            grouplists=grouplists,
            scanlists=scanlists,
            zones=sorted(zones, key=lambda z: z.Name),
        )

    def to_json(self, based_on=None):
        cp_dict = {}
        if based_on is not None:
            cp_dict = json.load(based_on)
        cp_dict.update(
            dict(
                Contacts=[c.to_dict() for c in self.contacts],
                Channels=[c.to_dict() for c in self.channels],
                GroupLists=[attr.asdict(c) for c in self.grouplists],
                ScanLists=[attr.asdict(c) for c in self.scanlists],
                Zones=[attr.asdict(c) for c in self.zones],
            )
        )
        return json.dumps(cp_dict, indent=2)


def pnwdigital_query_repeaters():
    return requests.get(PNWDIGITAL_REPEATERS)


def pnwdigital_query_sites():
    return requests.get(PNWDIGITAL_SITES)


def write_talkgroup_matrix(repeaters, fh):
    headers = ["Zone Name", "Comment", "Power", "RX Freq", "TX Freq", "Color Code"]
    headers.extend(
        sorted(tg.name_with_timeslot for tg in Talkgroup.all_talkgroups_by_id.values())
    )
    dw = csv.DictWriter(fh, headers, restval="-")
    dw.writeheader()
    for r in sorted(repeaters, key=lambda k: k.code):
        rdict = {
            "Zone Name": "{} {}".format(r.code, r.city),
            "Comment": "{} {}".format(r.name, r._site_id),
            "Power": "high",
            "RX Freq": str(r.frequency),
            "TX Freq": str(r.frequency + r.offset),
            "Color Code": str(r.color_code),
        }
        for tg in r.talkgroups:
            rdict[tg.name_with_timeslot] = str(tg.timeslot.value)
        dw.writerow(rdict)
