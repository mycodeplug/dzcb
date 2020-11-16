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
from pathlib import Path
import os

from dzcb.model import AnalogChannel, Codeplug, Contact, DigitalChannel, GroupList, ScanList, Talkgroup, Zone


def Talkgroups_map_from_csv(talkgroups_csv):
    talkgroups_by_name = {}
    for tg_name, tg_id in csv.reader(talkgroups_csv):
        talkgroups_by_name.setdefault(
            tg_name, 
            Contact(
                name=tg_name,
                dmrid=tg_id,
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
        ch.grouplist = GroupList(
            name="{} TGS".format(ch.code),
            contacts=[tg.name for tg in ch.static_talkgroups],
        )
        grouplists.append(ch.grouplist)

    all_channels = {}
    for zname, zchannels in zone_dicts.items():
        channel_names = []
        for ch in zchannels:
            if isinstance(ch, DigitalChannel):
                if ch.static_talkgroups:
                    update_static_talkgroups(ch)
                if ch.talkgroup:
                    contacts.add(ch.talkgroup)
            if ch.name not in all_channels:
                all_channels[ch.name] = ch
            channel_names.append(ch.name)
        zscanlist = ScanList(
            name=zname,
            channels=channel_names,
        )
        scanlists.append(zscanlist)
        for ch in zchannels:
            if ch.scanlist is None:
                ch.scanlist = zscanlist
        zones.append(
            Zone(
                name=zname,
                channels_a=channel_names,
                channels_b=channel_names,
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
        zname = r["Zone"]
        zname, found, code = zname.partition(";")
        name = r["Channel Name"]
        frequency = float(r["RX Freq"])
        offset = round(float(r["TX Freq"]) - frequency, 1)
        power = r["Power"]
        tone_encode = r["CTCSS Decode"] if r["CTCSS Decode"] != "Off" else None
        tone_decode = r["CTCSS Encode"] if r["CTCSS Encode"] != "Off" else None
        zones.setdefault(zname, []).append(
            AnalogChannel(
                name=name,
                code=code or None,
                frequency=frequency,
                offset=offset,
                tone_encode=tone_encode,
                tone_decode=tone_decode,
                power=power,
            )
        )
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
                        talkgroups_by_name[tg_name], timeslot,
                    )
                )
            except ValueError:
                print("Ignoring ValueError from {}:{}".format(tg_name, timeslot))
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
        talkgroup = Talkgroup.from_contact(
            talkgroups_by_name[tg_name], r.pop("TimeSlot"),
        )
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


def Codeplug_from_k7abd(input_dir):
    """
    :param input_dir: directory on the filesystem containing K7ABD ACB files
    :return: Codeplug
    """
    d = Path(input_dir)
    zones = {}
    talkgroups = {}
    all_talkgroups_by_name = {}
    for p in d.glob("Analog__*.csv"):
        zones.update(Analog_from_csv(p.read_text().splitlines()))
    for p in d.glob("Talkgroups__*.csv"):
        name = p.name.replace("Talkgroups__", "").replace(".csv", "")
        talkgroups[name] = Talkgroups_map_from_csv(p.read_text().splitlines())
        # XXX: potential bug here if talkgroup definitions differ between files
        all_talkgroups_by_name.update(talkgroups[name])
    for p in d.glob("Digital-Others__*.csv"):
        zones.update(DigitalChannels_from_k7abd_csv(p.read_text().splitlines(), all_talkgroups_by_name))
    for p in d.glob("Digital-Repeaters__*.csv"):
        zname = p.name.replace("Digital-Repeaters__", "").replace(".csv", "")
        zones[zname] = tuple(DigitalRepeaters_from_k7abd_csv(p.read_text().splitlines(), talkgroups[zname]))
    return Codeplug_from_zone_dicts(zones)
