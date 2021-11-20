"""
dzcb.k7abd - read k7abd anytone-codeplug-builder CSV files

These files are provided by PNWDigital and generated from repeaterbook CSV,
and fully describe how to build a complex code plug.

A k7abd is given as a directory or a .zip file and contains files of the
following format.

  * Analog__name-%Y-%m-%d.csv
    * Analog simplex and repeater frequencies. The "name" in the filename is
      not used. Only the Zone in the CSV makes it to the codeplug.
  * Digital-Others__name-%Y-%m-%d.csv
    * Digital simplex channels with 1:1 talkgroup mapping
  * Digital-Repeaters__name-%Y-%m-%d.csv
    * Digital repeater network provides talkgroup matrix
    * 1 channel is created per talkgroup per repeater. In this configuration
      the Zone name is the repeater name/code
  * Talkgroups__name-%Y-%m-%d.csv
    * Provides talkgroup name/number mapping
    * "name" in the filename should match with an associated Digital-Repeaters CSV
"""
import csv
import logging
from pathlib import Path

import attr

from dzcb.model import (
    AnalogChannel,
    Codeplug,
    Contact,
    ContactType,
    DigitalChannel,
    GroupList,
    ScanList,
    Talkgroup,
    Zone,
)
import dzcb.tone
from dzcb.util import unique_name


logger = logging.getLogger(__name__)

OFF = "Off"

ZONE = "Zone"
CHANNEL_NAME = "Channel Name"
BANDWIDTH = "Bandwidth"
POWER = "Power"
RX_FREQ = "RX Freq"
TX_FREQ = "TX Freq"
CTCSS_DECODE = "CTCSS Decode"
CTCSS_ENCODE = "CTCSS Encode"
TX_PROHIBIT = "TX Prohibit"
ANALOG_CSV_FIELDS = [
    ZONE,
    CHANNEL_NAME,
    BANDWIDTH,
    POWER,
    RX_FREQ,
    TX_FREQ,
    CTCSS_DECODE,
    CTCSS_ENCODE,
    TX_PROHIBIT,
]


def Talkgroups_map_from_csv(talkgroups_csv):
    talkgroups_by_name = {}
    for tg_name, tg_id in csv.reader(talkgroups_csv):
        ct_type = ContactType.GROUP
        if tg_id.endswith(("P", "p")):
            tg_id = tg_id[:-1]
            ct_type = ContactType.PRIVATE
        talkgroups_by_name.setdefault(
            tg_name,
            Contact(
                name=tg_name,
                dmrid=tg_id,
                kind=ct_type,
            ),
        )
    return talkgroups_by_name


def Codeplug_from_zone_dicts(zone_dicts):
    """
    :param zone_dicts: dict of ZoneName -> [DigitalChannel, AnalogChannel, etc... ]
    """
    contacts = set()
    channels = list()
    grouplists = list()
    scanlists = list()
    zones = list()

    def update_static_talkgroups(ch):
        contacts.update(ch.static_talkgroups)
        grouplist = GroupList(
            name="{} TGS".format(ch.code or ch.name[:5]),
            contacts=ch.static_talkgroups,
        )
        grouplists.append(grouplist)
        return attr.evolve(ch, grouplist=grouplist)

    all_channels = {}
    for zname, zchannels in zone_dicts.items():
        updated_channels = []
        zscanlist = ScanList(
            name=zname,
            channels=updated_channels,
        )
        for ch in zchannels:
            if isinstance(ch, DigitalChannel):
                if ch.static_talkgroups:
                    ch = update_static_talkgroups(ch)
                if ch.talkgroup:
                    contacts.add(ch.talkgroup)
            if ch.scanlist is None:
                ch = attr.evolve(ch, scanlist=zscanlist)
            # if the existing channel with this short name doesn't hash to
            # the current channel, then append a number until it does.
            # This will ensure all same short named channels get the same
            # unique suffix
            while all_channels.get(ch.short_name) not in (ch, None):
                ch = attr.evolve(ch, dedup_key=ch._dedup_key + 1)
            all_channels[ch.short_name] = ch
            updated_channels.append(ch)
        scanlists.append(attr.evolve(zscanlist, channels=updated_channels))
        zones.append(
            Zone(
                name=zname,
                channels_a=updated_channels,
                channels_b=updated_channels,
            )
        )
    channels.extend(all_channels.values())
    return Codeplug(
        contacts=sorted(list(contacts), key=lambda c: c.name),
        channels=channels,
        grouplists=grouplists,
        scanlists=sorted(list(scanlists), key=lambda s: s.name),
        zones=sorted(zones, key=lambda z: z.name),
    )


def Analog_from_csv(analog_repeaters_csv):
    zones = {}
    csvr = csv.DictReader(analog_repeaters_csv)
    for r in csvr:
        try:
            zname = r[ZONE]
            zname, found, code = zname.partition(";")
            name = r[CHANNEL_NAME]
            frequency = float(r[RX_FREQ])
            offset = round(float(r[TX_FREQ]) - frequency, 1)
            power = r[POWER]
            bandwidth = r[BANDWIDTH].rstrip("K")
            tone_encode = (
                r[CTCSS_ENCODE] if r[CTCSS_ENCODE].lower() not in ("off", "") else None
            )
            tone_decode = (
                r[CTCSS_DECODE] if r[CTCSS_DECODE].lower() not in ("off", "") else None
            )
            zones.setdefault(zname, []).append(
                AnalogChannel(
                    name=name,
                    code=code or None,
                    frequency=frequency,
                    offset=offset,
                    tone_encode=tone_encode,
                    tone_decode=tone_decode,
                    power=power,
                    bandwidth=bandwidth,
                )
            )
        except ValueError as ve:
            logger.info("Skipping channel {} / {}: {}".format(zname, name, ve))
    return zones


def DigitalRepeaters_from_k7abd_csv(digital_repeaters_csv, talkgroups_by_name):
    """
    read a talkgroup matrix and yield DigitalChannel

    :param digital_repeaters_csv: iterable of CSV lines: ... see code ;]
    :param talkgroups_by_name: map of tg_name -> Talkgroup
    :return: iterable of DigitalChannel with static_talkgroups ready to be expanded
        and converted into group/scan lists.
    """
    csvr = csv.DictReader(digital_repeaters_csv)
    for r in csvr:
        _ = r.pop("Comment", None)
        zname, found, code = r.pop("Zone Name").partition(";")
        frequency = float(r.pop("RX Freq"))
        if not frequency:
            logger.info(
                "%s: Excluding repeater, %s with no frequency",
                digital_repeaters_csv,
                zname,
            )
            continue
        offset = round(float(r.pop("TX Freq")) - frequency, 1)
        color_code = r.pop("Color Code")
        power = r.pop("Power")
        talkgroups = []
        for tg_name, timeslot in r.items():
            if timeslot.strip() == "-":
                continue
            try:
                talkgroups.append(
                    Talkgroup.from_contact(
                        talkgroups_by_name[tg_name],
                        timeslot,
                    )
                )
            except KeyError:
                logger.warning(
                    "'%s' references unknown talkgroup '%s'. Ignored.",
                    zname,
                    tg_name,
                )
            except ValueError:
                logger.info(
                    "%s: Ignoring ValueError from %s:%s",
                    digital_repeaters_csv,
                    tg_name,
                    timeslot,
                )
        repeater = DigitalChannel(
            name=zname,
            code=code or None,
            frequency=frequency,
            offset=offset,
            color_code=color_code,
            power=power,
            static_talkgroups=sorted(talkgroups, key=lambda tg: tg.name),
        )
        yield repeater


def DigitalChannels_from_k7abd_csv(digital_others_csv, talkgroups_by_name):
    """
    read a Digital-Others files and yield DigitalChannel

    :param digital_others_csv: iterable of CSV lines: ... see code ;]
    :param talkgroups_by_name: map of tg_name -> Talkgroup
    :return: dict of zone_name -> tuple of DigitalChannel (with talkgroup set)
    """
    zones = {}
    csvr = csv.DictReader(digital_others_csv)
    for r in csvr:
        _ = r.pop("Comment", None)
        zname, found, code = r.pop("Zone Name", r.pop("Zone")).partition(";")
        name = r.pop("Channel Name")
        frequency = float(r.pop("RX Freq"))
        offset = round(float(r.pop("TX Freq")) - frequency, 1)
        color_code = r.pop("Color Code")
        power = r.pop("Power")
        tg_name = r.pop("Talk Group")
        try:
            talkgroup = Talkgroup.from_contact(
                talkgroups_by_name[tg_name],
                r.pop("TimeSlot"),
            )
        except KeyError:
            logger.warning(
                "'%s/%s' references unknown talkgroup '%s'. Ignored.",
                zname,
                name,
                tg_name,
            )
            continue
        zones.setdefault(zname, []).append(
            DigitalChannel(
                name=name,
                code=code or None,
                frequency=frequency,
                offset=offset,
                color_code=color_code,
                power=power,
                talkgroup=talkgroup,
            )
        )
    return zones


def _log_zones_channels(in_zones, log_filename=None, level=logging.DEBUG):
    filename_str = ""
    if log_filename:
        filename_str = " from {}".format(log_filename)
    total_channels = sum(len(z) for z in in_zones.values())
    logger.log(
        level,
        "Load %s zones (%s channels)%s",
        len(in_zones),
        total_channels,
        filename_str,
    )


def update_zones_channels(zones_dict, in_zones, log_filename=None):
    """
    Update `zones_dict` with the contents of `in_zones`

    :param log_filename: used for logging only
    """
    _log_zones_channels(in_zones, log_filename)
    for zname, zchannels in in_zones.items():
        zones_dict[unique_name(zname, zones_dict)] = zchannels


def Codeplug_from_k7abd(input_dir):
    """
    :param input_dir: directory on the filesystem containing K7ABD ACB files
    :return: Codeplug
    """
    d = Path(input_dir)
    zones = {}
    talkgroups = {}
    all_talkgroups_by_name = {}
    total_files = 0
    if not dzcb.tone.REQUIRE_VALID_TONE:
        logger.warning(
            "REQUIRE_VALID_TONE=0: resulting codeplug files may contain invalid entries"
        )
    for p in sorted(d.glob("Analog__*.csv")):
        update_zones_channels(
            zones, Analog_from_csv(p.read_text().splitlines()), log_filename=p
        )
        total_files += 1
    for p in sorted(d.glob("Talkgroups__*.csv")):
        name = p.name.replace("Talkgroups__", "").replace(".csv", "")
        talkgroups[name] = Talkgroups_map_from_csv(p.read_text().splitlines())
        logger.debug("Load %s talkgroups from %s", len(talkgroups[name]), p)
        # XXX: potential bug here if talkgroup definitions differ between files
        all_talkgroups_by_name.update(talkgroups[name])
    for p in sorted(d.glob("Digital-Others__*.csv")):
        update_zones_channels(
            zones,
            DigitalChannels_from_k7abd_csv(
                p.read_text().splitlines(), all_talkgroups_by_name
            ),
            log_filename=p,
        )
        total_files += 1
    for p in sorted(d.glob("Digital-Repeaters__*.csv")):
        zname = p.name.replace("Digital-Repeaters__", "").replace(".csv", "")
        # merge Talkgroup files, but prefer talkgroup names from this zone
        tg_csv = all_talkgroups_by_name.copy()
        try:
            tg_csv.update(talkgroups[zname])
        except KeyError:
            logger.debug("Talkgroups__%s.csv was not found. Ignored.", zname)
        update_zones_channels(
            zones,
            {
                zname: tuple(
                    DigitalRepeaters_from_k7abd_csv(p.read_text().splitlines(), tg_csv)
                )
            },
            log_filename=p,
        )
        total_files += 1
    _log_zones_channels(
        in_zones=zones,
        log_filename="{} total files".format(total_files),
        level=logging.INFO,
    )
    return Codeplug_from_zone_dicts(zones)
