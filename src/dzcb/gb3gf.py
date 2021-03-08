"""
Write series of CSV files acceptable for import into gb3gf codeplug tool

Ex: OpenGD77
"""
import csv
import logging

from dzcb.model import AnalogChannel, Bandwidth

logger = logging.getLogger(__name__)

SUPPORTED_RADIOS = ("opengd77", )
DEFAULT_SUPPORTED_RADIOS = ("opengd77", )

# These talkgroups are removed until the TG list is 32 channels or less
TALKGROUP_LIST_OVERFLOW = [
    "Michigan 1",
    "Ontario 2",
    "PS1-DNU",
    "PS2-DNU",
    "SNARS 1-2",
    "USA 2",
    "Worldwide 2",
    "TAC Eng 123",
    "WW English 2",
    "SoCal 2",
    "Audio Test 2",
]

# TG_List Overflow (These are removed if there are > 77 TG Lists)
TG_LIST_OVERFLOW = ["MMP TGS"]
TG_LIST_MAX = 76
NAME_MAX = 16

value_replacements = {
    None: "None",
    False: "No",
    True: "Yes",
}


def Codeplug_to_gb3gf_opengd77_csv(cp, output_dir):
    # filter down to supported frequency ranges
    cp = cp.filter(ranges=((136.0, 174.0), (400.0, 480.0)))
    # will keep track of contacts separately and write them at the end
    # using name_with_timeslot
    contacts = set()
    # Channels.csv, Contacts.csv, TG_List.csv, Zones.csv
    channel_fields = [
        "Channel Number",
        "Channel Name",
        "Channel Type",
        "Rx Frequency",
        "Tx Frequency",
        "Colour Code",
        "Timeslot",
        "Contact",
        "TG List",
        "RX Tone",
        "TX Tone",
        "Power",
        "Bandwidth",
        "Squelch",
        "Rx Only",
        "Zone Skip",
        "All Skip",
        "TOT",
        "VOX",
    ]
    with open("{}/Channels.csv".format(output_dir), "w", newline="") as f:
        csvw = csv.DictWriter(f, channel_fields, delimiter=";")
        csvw.writeheader()
        for ix, channel in enumerate(cp.channels):
            if isinstance(channel, AnalogChannel):
                d = {
                    "Channel Type": "Analog",
                    "RX Tone": channel.tone_decode or "None",
                    "TX Tone": channel.tone_encode or "None",
                    "Colour Code": "None",
                    "Contact": "N/A",
                    "TG List": "None",
                }
            else:
                d = {
                    "Channel Type": "Digital",
                    "RX Tone": "None",
                    "TX Tone": "None",
                    "Colour Code": channel.color_code,
                    "Contact": "N/A",
                    "TG List": channel.grouplist_name(cp) if channel.grouplist else "None",
                }
                if channel.talkgroup:
                    d["Contact"] = channel.talkgroup.name_with_timeslot
                    contacts.add(channel.talkgroup)
            d.update(
                {
                    "Channel Number": ix + 1,
                    "Channel Name": channel.short_name,
                    "Rx Frequency": channel.frequency,
                    "Tx Frequency": round(channel.frequency + channel.offset, 5),
                    "Timeslot": 1,
                    "Power": str(channel.power),
                    "Bandwidth": channel.bandwidth.flattened([Bandwidth._25, Bandwidth._125]).value + "KHz",
                    "Squelch": str(channel.squelch) if channel.squelch else "Disabled",
                    "Rx Only": value_replacements[channel.rx_only],
                    "Zone Skip": "No",
                    "All Skip": "No",
                    "TOT": 90,
                    "VOX": "No",
                }
            )
            csvw.writerow(d)
    tg_fields = ["TG List Name"] + ["Contact {}".format(x) for x in range(1, 33)]
    with open("{}/TG_Lists.csv".format(output_dir), "w", newline="") as f:
        csvw = csv.DictWriter(f, tg_fields, delimiter=";")
        csvw.writeheader()
        n_grouplists = len(cp.grouplists)
        for gl in cp.grouplists:
            if n_grouplists > TG_LIST_MAX and gl.name in TG_LIST_OVERFLOW:
                n_grouplists -= 1
                continue
            tg_list = {"TG List Name": gl.name}
            contacts_by_name = {tg.name: tg for tg in gl.contacts}
            remove_tgs = list(reversed(TALKGROUP_LIST_OVERFLOW))
            # remove some talkgroups to get under the limit
            while len(contacts_by_name) > 32:
                try:
                    del contacts_by_name[remove_tgs.pop()]
                except KeyError:
                    pass
            for ix, tg in enumerate(contacts_by_name.values()):
                tg_list["Contact {}".format(ix + 1)] = tg.name_with_timeslot
                contacts.add(tg)
            csvw.writerow(tg_list)
    zone_fields = ["Zone Name"] + ["Channel {}".format(x) for x in range(1, 81)]
    with open("{}/Zones.csv".format(output_dir), "w", newline="") as f:
        csvw = csv.DictWriter(f, zone_fields, delimiter=";")
        csvw.writeheader()
        zone_names = [z.name for z in cp.zones]
        # OpenGD77 doesn't have scanlist, so simulate it with separate zones
        write_zones = [sl for sl in cp.scanlists if sl.name not in zone_names]
        write_zones.extend(cp.zones)
        for zone in write_zones:
            row = {"Zone Name": zone.name}
            for ix, ch in enumerate(zone.unique_channels):
                if ix + 1 > 80:
                    logger.debug("Zone '%s' exceeds 80 channels", zone.name)
                    break
                row["Channel {}".format(ix + 1)] = ch.short_name
            csvw.writerow(row)
    with open("{}/Contacts.csv".format(output_dir), "w", newline="") as f:
        csvw = csv.DictWriter(
            f, ["Contact Name", "ID", "ID Type", "TS Override"], delimiter=";"
        )
        csvw.writeheader()
        for tg in sorted(contacts, key=lambda c: c.name_with_timeslot):
            csvw.writerow(
                {
                    "Contact Name": tg.name_with_timeslot,
                    "ID": tg.dmrid,
                    "ID Type": str(tg.kind),
                    "TS Override": str(tg.timeslot),
                }
            )
    logger.info("Wrote GB3GF OpenGD77 CSV files to '%s'", output_dir)
