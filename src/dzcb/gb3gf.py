"""
Write series of CSV files acceptable for import into gb3gf codeplug tool

Ex: OpenGD77
"""
import csv

from dzcb.model import AnalogChannel, DigitalChannel
import dzcb.munge

# These channels are my favorite XXX: use a data file
POPLAR_SCAN = "Poplar Scan;Longview/Rainier;DPHS Static;DPHS Wide;W7DG Longview ;N7EI Deer Island;W7BU Astoria Nic;W7BU Astoria Wic;K7RPT Astoria Wi;KJ7IY Timber ;WA7UHD Chehalis ;N3EG Longview Co;AB7F Longview ;W7OTV Colton Goa;SP U01 441.000;SP U02 446.5;SP U03 446.075;SP U04 433.45;SP U05 430.4125;SP U06 439.4125;SP U07 430.425;SP U08 439.425;SP V01 145.790;SP V02 145.510;FRS 1;FRS 2;FRS 3;FRS 4;FRS 5;FRS 6;FRS 7;FRS 8 (IS);FRS 9 (IS);FRS 10 (IS);FRS 11 (IS);FRS 12 (IS);FRS 13 (IS);FRS 14 (IS);GMRS 1 (15);GMRS 2 (16);GMRS 3 (17);GMRS 4 (18);GMRS 5 (19);GMRS 6 (20);GMRS 7 (21);GMRS 8 (22);FM 146.52;FM 446.000;MURS 1;MURS 2;MURS 3;MURS 4 (Blue);MURS 5 (Green);FM 146.53;FM 146.54;FM 146.55;FM 146.56;FM 146.57;FM 146.58;FM 147.52;FM 147.53;FM 147.54;FM 147.55;FM 147.56;FM 147.57;FM 147.58;FM 147.59;FM 147.60;FM 446.025;FM 445.8;FM 445.825;FM 445.85;FM 445.875;FM 445.9;FM 445.975;;;;;;;\n"

# These talkgroups are removed until the TG list is 32 channels or less
TALKGROUP_LIST_OVERFLOW = ["Michigan 1", "Ontario 2", "PS1-DNU", "PS2-DNU", "SNARS 1~2", "USA 2", "Worldwide 2", "TAC Eng 123", "WW English 2", "SoCal 2", "Audio Test 2"]

# TG_List Overflow (These are removed if there are > 77 TG Lists)
TG_LIST_OVERFLOW = ["MMP TGS"]
TG_LIST_MAX = 76
NAME_MAX = 16

value_replacements = {
    None: "None",
    False: "No",
    True: "Yes",
}


def filter_zones(zones, order=None):
    if order is None:
        order=[
            # XXX: for the quick of it quick of it
            "PNWDigital",
            "Hotspot",
            "Local",
            "SeattleDMR",
            "Longview WA VHF 35mi",
            "Longview WA UHF 35mi",
            "Simplex A VHF",
            "Simplex A UHF",
            "Simplex D VHF",
            "Simplex D UHF",
        ]
    return dzcb.munge.ordered(zones, order, key=lambda z: z.name)

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
                    "Tx Frequency": round(channel.frequency + channel.offset, 5),
                    "Timeslot": 1,
                    "Power": str(channel.power),
                    "Bandwidth": "25KHz" if channel.bandwidth > 19 else "12.5KHz",
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
        n_grouplists = len(cp.grouplists)
        for gl in cp.grouplists:
            if n_grouplists > TG_LIST_MAX and gl.name in TG_LIST_OVERFLOW:
                n_grouplists -= 1
                continue
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
        # XXX: Make this more general
        f.write(POPLAR_SCAN)
        for zone in filter_zones(cp.zones):
            row = {"Zone Name": zone.name}
            for ix, ch in enumerate(zone.unique_channels):
                if ix + 1 > 80:
                    print("Zone {} exceeds 80 channels".format(zone.name))
                    break
                row["Channel {}".format(ix + 1)] = dzcb.munge.channel_name(ch, NAME_MAX)
            csvw.writerow(row)

