"""
Write series of CSV files acceptable for import into Anytone CPS tool

Supported CPS versions

    578: 1.11
    868: 1.39
    878: 1.21

"""
import csv
import logging
from pathlib import Path

from dzcb import AMATEUR_220, COMMERCIAL_UHF, COMMERCIAL_VHF
from dzcb.model import AnalogChannel, DigitalChannel

logger = logging.getLogger(__name__)

NAME_MAX = 16
SCANLIST_MAX = 50
OFF = "Off"
ON = "On"
NONE = "None"

value_replacements = {
    None: NONE,
    False: OFF,
    True: ON,
}

format_frequency = "{:.5f}".format
format_channel_type = {
    AnalogChannel: "A-Analog",
    DigitalChannel: "D-Digital",
}.get


def format_member_list(members, list_name, expand_members=False):
    d = {list_name: "|".join(m.short_name for m in members)}
    if expand_members:
        d.update(
            {
                list_name
                + " RX Frequency": "|".join(
                    format_frequency(m.frequency) for m in members
                ),
                list_name
                + " TX Frequency": "|".join(
                    format_frequency(m.frequency + m.offset) for m in members
                ),
            }
        )
    return d


def replace_field_names(d, model):
    for orig, repl in model.get("replace_field_names", {}).items():
        if orig in d:
            d[repl] = d[orig]
            del d[orig]
    return d


# 578/868/878 Common Talkgroups.CSV format
talkgroup_fields = ("No.", "Radio ID", "Name", "Call Type", "Call Alert")
talkgroup_filename = "TalkGroups.CSV"
talkgroup_filename_578_1_11 = "ContactTalkGroups.CSV"

channel_fields_578_1_11 = {
    "No.": None,
    "Channel Name": None,
    "Receive Frequency": None,
    "Transmit Frequency": None,
    "Channel Type": None,
    "Transmit Power": "High",
    "Band Width": "25K",
    "CTCSS/DCS Decode": OFF,
    "CTCSS/DCS Encode": OFF,
    "Contact": "",
    "Contact Call Type": "Group Call",
    "Contact TG/DMR ID": "0",
    "Radio ID": "",
    "Busy Lock/TX Permit": "Always",
    "Squelch Mode": "Carrier",
    "Optional Signal": OFF,
    "DTMF ID": "1",
    "2Tone ID": "1",
    "5Tone ID": "1",
    "PTT ID": OFF,
    "Color Code": "1",
    "Slot": "1",
    "Scan List": NONE,
    "Receive Group List": NONE,
    "PTT Prohibit": OFF,
    "Reverse": OFF,
    "TDMA": OFF,
    "TDMA Adaptive": OFF,
    "AES Digital Encryption": "Normal Encryption",
    "Digital Encryption": OFF,
    "Call Confirmation": OFF,
    "Talk Around(Simplex)": OFF,
    "Work Alone": OFF,
    "Custom CTCSS": "251.1",
    "2TONE Decode": "0",
    "Ranging": OFF,
    "Simplex": OFF,
    "Digi APRS RX": OFF,
    "Analog APRS PTT Mode": OFF,
    "Digital APRS PTT Mode": OFF,
    "APRS Report Type": OFF,
    "Digital APRS Report Channel": "1",
    "Correct Frequency[Hz]": "0",
    "SMS Confirmation": OFF,
    "Exclude Channel From Roaming": "0",
    "DMR MODE": "0",
    "DataACK Disable": "0",
    "R5toneBot": "0",
    "R5ToneEot": "0",
}
channel_fields_868_1_39 = {
    "No.": None,
    "Channel Name": None,
    "Receive Frequency": None,
    "Transmit Frequency": None,
    "Channel Type": None,
    "Transmit Power": "High",
    "Band Width": "25K",
    "CTCSS/DCS Decode": OFF,
    "CTCSS/DCS Encode": OFF,
    "Contact": "",
    "Contact Call Type": "Group Call",
    "Radio ID": "",
    "Busy Lock/TX Permit": "Always",
    "Squelch Mode": "Carrier",
    "Optional Signal": OFF,
    "DTMF ID": "1",
    "2Tone ID": "1",
    "5Tone ID": "1",
    "PTT ID": OFF,
    "Color Code": "1",
    "Slot": "1",
    "CH Scan List": NONE,
    "Receive Group List": NONE,
    "TX Prohibit": OFF,
    "Reverse": OFF,
    "Simplex TDMA": OFF,
    "TDMA Adaptive": OFF,
    "Encryption Type": "Normal Encryption",
    "Digital Encryption": OFF,
    "Call Confirmation": OFF,
    "Talk Around": OFF,
    "Work Alone": OFF,
    "Custom CTCSS": "251.1",
    "2TONE Decode": "0",
    "Ranging": OFF,
    "Through Mode": OFF,
    "APRS Report": OFF,
    "APRS Report Channel": "1",
}
channel_fields_878_1_21 = {
    "No.": None,
    "Channel Name": None,
    "Receive Frequency": None,
    "Transmit Frequency": None,
    "Channel Type": None,
    "Transmit Power": "High",
    "Band Width": "25K",
    "CTCSS/DCS Decode": OFF,
    "CTCSS/DCS Encode": OFF,
    "Contact": "",
    "Contact Call Type": "Group Call",
    "Contact TG/DMR ID": "0",
    "Radio ID": "",
    "Busy Lock/TX Permit": "Always",
    "Squelch Mode": "Carrier",
    "Optional Signal": OFF,
    "DTMF ID": "1",
    "2Tone ID": "1",
    "5Tone ID": "1",
    "PTT ID": OFF,
    "Color Code": "1",
    "Slot": "1",
    "Scan List": NONE,
    "Receive Group List": NONE,
    "PTT Prohibit": OFF,
    "Reverse": OFF,
    "Simplex TDMA": OFF,
    "Slot Suit": OFF,
    "AES Digital Encryption": "Normal Encryption",
    "Digital Encryption": OFF,
    "Call Confirmation": OFF,
    "Talk Around(Simplex)": OFF,
    "Work Alone": OFF,
    "Custom CTCSS": "251.1",
    "2TONE Decode": "0",
    "Ranging": OFF,
    "Through Mode": OFF,
    "Digi APRS RX": OFF,
    "Analog APRS PTT Mode": OFF,
    "Digital APRS PTT Mode": OFF,
    "APRS Report Type": OFF,
    "Digital APRS Report Channel": "1",
    "Correct Frequency[Hz]": "0",
    "SMS Confirmation": OFF,
    "Exclude Channel From Roaming": "0",
    "DMR MODE": "0",
    "DataACK Disable": "0",
    "R5toneBot": "0",
    "R5ToneEot": "0",
}
channel_filename = "Channel.CSV"

scanlist_fields_578_1_11 = {
    "No.": None,
    "Scan List Name": None,
    "Scan Channel Member": None,
    "Scan Channel Member RX Frequency": None,
    "Scan Channel Member TX Frequency": None,
    "Scan Mode": OFF,
    "Priority Channel Select": "Priority Channel Select1",
    "Priority Channel 1": "Current Channel",
    "Priority Channel 1 RX Frequency": "",
    "Priority Channel 1 TX Frequency": "",
    "Priority Channel 2": OFF,
    "Priority Channel 2 RX Frequency": "",
    "Priority Channel 2 TX Frequency": "",
    "Revert Channel": "Selected",
    "Look Back Time A[s]": "2.0",
    "Look Back Time B[s]": "3.0",
    "Dropout Delay Time[s]": "3.1",
    "Dwell Time[s]": "3.1",
}
scanlist_fields_868_1_39 = {
    "No.": None,
    "Scan List Name": None,
    "Scan Channel Member": None,
    "Scan Mode": OFF,
    "Priority Channel Select": "Priority Channel Select1",
    "Priority Channel 1": "Current Channel",
    "Priority Channel 2": OFF,
    "Revert Channel": "Selected",
    "Look Back Time A[s]": "2.0",
    "Look Back Time B[s]": "3.0",
    "Dropout Delay Time[s]": "3.1",
    "Dwell Time[s]": "3.1",
}
scanlist_filename = "ScanList.CSV"

zone_fields_578_1_11 = {
    "No.": None,
    "Zone Name": None,
    "Zone Channel Member": None,
    "Zone Channel Member RX Frequency": None,
    "Zone Channel Member TX Frequency": None,
    "A Channel": None,
    "A Channel RX Frequency": None,
    "A Channel TX Frequency": None,
    "B Channel": None,
    "B Channel RX Frequency": None,
    "B Channel TX Frequency": None,
}
zone_fields_868_1_39 = {
    "No.": None,
    "Zone Name": None,
    "Zone Channel Member": None,
    "A Channel": None,
    "B Channel": None,
}
zone_filename = "Zone.CSV"

SUPPORTED_RADIOS = {
    "578_1_11": dict(
        version="1.11",
        expand_members=True,
        frequency_range=(COMMERCIAL_VHF, AMATEUR_220, COMMERCIAL_UHF),
        channel=channel_fields_578_1_11,
        channel_filename=channel_filename,
        scanlist=scanlist_fields_578_1_11,
        scanlist_filename=scanlist_filename,
        zone=zone_fields_578_1_11,
        zone_filename=zone_filename,
        talkgroup=talkgroup_fields,
        talkgroup_filename=talkgroup_filename_578_1_11,
        replace_field_names={},
    ),
    "868_1_39": dict(
        version="1.39",
        expand_members=False,
        frequency_range=(COMMERCIAL_VHF, COMMERCIAL_UHF),
        channel=channel_fields_868_1_39,
        channel_filename=channel_filename,
        scanlist=scanlist_fields_868_1_39,
        scanlist_filename=scanlist_filename,
        zone=zone_fields_868_1_39,
        zone_filename=zone_filename,
        talkgroup=talkgroup_fields,
        talkgroup_filename=talkgroup_filename,
        replace_field_names={
            "PTT Prohibit": "TX Prohibit",
            "Scan List": "CH Scan List",
        },
    ),
    "878_1_21": dict(
        version="1.21",
        expand_members=True,
        frequency_range=(COMMERCIAL_VHF, COMMERCIAL_UHF),
        channel=channel_fields_878_1_21,
        channel_filename=channel_filename,
        scanlist=scanlist_fields_578_1_11,
        scanlist_filename=scanlist_filename,
        zone=zone_fields_578_1_11,
        zone_filename=zone_filename,
        talkgroup=talkgroup_fields,
        talkgroup_filename=talkgroup_filename,
        replace_field_names={},
    ),
}


def Codeplug_to_anytone_csv(cp, output_dir, models=None):
    if models is None:
        models = tuple(SUPPORTED_RADIOS.keys())
    for model_id in models:
        radio_dir = Path(output_dir) / model_id
        radio_dir.mkdir(parents=True, exist_ok=True)
        model = SUPPORTED_RADIOS[model_id]
        # filter down to supported frequency ranges
        mcp = cp.filter_frequency_range(*model["frequency_range"])
        with (radio_dir / model["talkgroup_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, model["talkgroup"])
            csvw.writeheader()
            for ix, tg in enumerate(mcp.contacts):
                csvw.writerow(
                    {
                        "No.": str(ix + 1),
                        "Radio ID": str(tg.dmrid),
                        "Name": tg.name,
                        "Call Type": str(tg.kind) + " Call",
                        "Call Alert": NONE,
                    }
                )
        with (radio_dir / model["channel_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["channel"].keys()))
            csvw.writeheader()
            for ix, channel in enumerate(mcp.channels):
                d = model["channel"].copy()
                if isinstance(channel, AnalogChannel):
                    d.update(
                        {
                            "CTCSS/DCS Decode": channel.tone_decode or "None",
                            "CTCSS/DCS Encode": channel.tone_encode or "None",
                            "Squelch Mode": "CTCSS/DCS"
                            if channel.tone_decode
                            else "Carrier",
                        }
                    )
                else:
                    d.update(
                        {
                            "Contact": channel.talkgroup.name
                            if channel.talkgroup
                            else "",
                            "Contact Call Type": str(channel.talkgroup.kind) + " Call",
                            "Color Code": str(channel.color_code),
                            "Slot": str(channel.talkgroup.timeslot),
                            "Scan List": channel.scanlist,
                            # TODO: Support group list
                        }
                    )
                d.update(
                    {
                        "No.": str(ix + 1),
                        "Channel Name": channel.short_name,
                        "Receive Frequency": format_frequency(channel.frequency),
                        "Transmit Frequency": format_frequency(
                            channel.frequency + channel.offset
                        ),
                        "Channel Type": format_channel_type(type(channel)),
                        "Transmit Power": str(channel.power),
                        "Band Width": "25K" if channel.bandwidth > 19 else "12.5K",
                        "PTT Prohibit": value_replacements[channel.rx_only],
                    }
                )
                csvw.writerow(replace_field_names(d, model))
        with (radio_dir / model["zone_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["zone"].keys()))
            csvw.writeheader()
            for ix, zone in enumerate(mcp.zones):
                d = {
                    "No.": str(ix + 1),
                    "Zone Name": zone.name,
                }
                d.update(
                    format_member_list(
                        members=zone.unique_channels,
                        list_name="Zone Channel Member",
                        expand_members=model["expand_members"],
                    )
                )
                [
                    d.update(
                        format_member_list(
                            members=(zone.unique_channels[0],),
                            list_name=list_name,
                            expand_members=model["expand_members"],
                        )
                    )
                    for list_name in ("A Channel", "B Channel")
                ]
                csvw.writerow(d)
        with (radio_dir / model["scanlist_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["scanlist"].keys()))
            csvw.writeheader()
            for ix, sl in enumerate(mcp.scanlists):
                d = model["scanlist"].copy()
                d.update(
                    {
                        "No.": str(ix + 1),
                        "Scan List Name": sl.name,
                    }
                )
                d.update(
                    format_member_list(
                        members=sl.unique_channels[:SCANLIST_MAX],
                        list_name="Scan Channel Member",
                        expand_members=model["expand_members"],
                    )
                )
                csvw.writerow(d)
        logger.info("Wrote Anytone %s CSV files to '%s'", model_id, radio_dir)
