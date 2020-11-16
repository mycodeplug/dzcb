"""
Write series of CSV files acceptable for import into gb3gf codeplug tool

Ex: OpenGD77
"""
import csv

from dzcb.model import AnalogChannel, DigitalChannel
import dzcb.munge

# These talkgroups are removed until the TG list is 32 channels or less
TALKGROUP_LIST_OVERFLOW = ["Michigan 1", "Ontario 2" "PS1-DNU", "PS2-DNU", "SNARS 1~2", "USA 2", "Worldwide 2", "TAC Eng 123", "WW English 2"]
NAME_MAX = 16

value_replacements = {
    None: "None",
    False: "No",
    True: "Yes",
}

def Codeplug_to_gb3gf_opengd77_csv(cp, output_dir):
    # Channels.csv, Contacts.csv, TG_List.csv, Zones.csv
    with open("{}/Contacts.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(
            f, ["Contact Name", "ID", "ID Type", "TS Override"], delimiter=";"
        )
        csvw.writeheader()
        for tg in cp.contacts:
            csvw.writerow(
                {
                    "Contact Name": tg.name,
                    "ID": tg.dmrid,
                    "ID Type": str(tg.kind),
                    "TS Override": str(tg.timeslot),
                }
            )
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
    with open("{}/Channels.csv".format(output_dir), "w") as f:
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
                    "Contact": channel.talkgroup.name if channel.talkgroup else "N/A",
                    "TG List": channel.grouplist.name if channel.grouplist else "None",
                }
            d.update(
                {
                    "Channel Number": ix + 1,
                    "Channel Name": dzcb.munge.channel_name(channel.name, NAME_MAX),
                    "Rx Frequency": channel.frequency,
                    "Tx Frequency": channel.frequency + channel.offset,
                    "Timeslot": 1,
                    "Power": str(channel.power),
                    "Bandwidth": str(channel.bandwidth) + "KHz",
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
    with open("{}/TG_Lists.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(f, tg_fields, delimiter=";")
        csvw.writeheader()
        for gl in cp.grouplists:
            tg_list = {"TG List Name": gl.name}
            contacts = list(gl.contacts)
            remove_tgs = list(reversed(TALKGROUP_LIST_OVERFLOW))
            # remove some talkgroups to get under the limit
            while len(contacts) > 32:
                try:
                    contacts.remove(remove_tgs.pop())
                except ValueError:
                    pass
            for ix, tg in enumerate(contacts):
                tg_list["Contact {}".format(ix + 1)] = tg
            csvw.writerow(tg_list)
    zone_fields = ["Zone Name"] + ["Channel {}".format(x) for x in range(1, 81)]
    with open("{}/Zones.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(f, zone_fields, delimiter=";")
        csvw.writeheader()
        for zone in cp.zones:
            row = {"Zone Name": zone.name}
            for ix, ch in enumerate(zone.unique_channels):
                if ix + 1 > 80:
                    print("Zone {} exceeds 80 channels".format(zone.name))
                    break
                row["Channel {}".format(ix + 1)] = dzcb.munge.channel_name(ch, NAME_MAX)
            csvw.writerow(row)

