"""
Write series of CSV files acceptable for import into Anytone CPS tool

Supported CPS versions

    578: 1.11
    868: 1.39
    878: 1.21

"""
import csv
import enum
import logging
from pathlib import Path

from dzcb import AMATEUR_220, COMMERCIAL_UHF, COMMERCIAL_VHF
from dzcb.model import AnalogChannel, Bandwidth, DigitalChannel, uniquify_contacts

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


def remove_fields(d, model):
    for f in model.get("remove_fields", []):
        if f in d:
            del d[f]
    return d


class DMR_MODE(enum.Enum):
    SIMPLEX = 0
    REPEATER = 1
    DUAL_SLOT = 2

    @classmethod
    def value_from(cls, channel):
        if abs(channel.offset) > 0:
            return cls.REPEATER.value
        return cls.SIMPLEX.value


class TXPermit(enum.Enum):
    ALWAYS = "Always"
    CHANNELFREE = "ChannelFree"
    SAMECOLOR = "Same Color Code"
    DIFFERENTCOLOR = "Different Color Code"

    @classmethod
    def value_from(cls, channel):
        if abs(channel.offset) > 0:
            return cls.SAMECOLOR.value
        return cls.ALWAYS.value


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
        replace_field_names={
            "Through Mode": "Simplex",
        },
        remove_fields=[],
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
        remove_fields=["Contact TG/DMR ID", "DMR MODE"],
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
        remove_fields=[],
    ),
}

DEFAULT_SUPPORTED_RADIOS = ("578_1_11", "868_1_39", "878_1_21")


def Talkgroup_to_dict(index, talkgroup):
    return {
        "No.": str(index + 1),
        "Radio ID": str(talkgroup.dmrid),
        "Name": talkgroup.name,
        "Call Type": str(talkgroup.kind) + " Call",
        "Call Alert": NONE,
    }


def Talkgroup_to_channel_detail(talkgroup):
    return {
        "Contact": talkgroup.name,
        "Contact Call Type": str(talkgroup.kind) + " Call",
        "Contact TG/DMR ID": talkgroup.dmrid,
        "Slot": str(talkgroup.timeslot),
    }


def AnalogChannel_to_dict(channel):
    return {
        "CTCSS/DCS Decode": channel.tone_decode or OFF,
        "CTCSS/DCS Encode": channel.tone_encode or OFF,
        "Squelch Mode": "CTCSS/DCS" if channel.tone_decode else "Carrier",
        "Busy Lock/TX Permit": OFF,
    }


def DigitalChannel_to_dict(channel):
    d = {
        "Color Code": str(channel.color_code),
        "Busy Lock/TX Permit": TXPermit.value_from(channel),
        "DMR MODE": DMR_MODE.value_from(channel),
        # On the 578 and 878, DMR MODE = "Simplex" (0) channels
        # also have "Simplex=On" and "Through Mode=On" in the
        # exported file. Neither targeted CPS version exposes
        # this setting in the UI. But the 578 1.11 CPS will show
        # DMR MODE "Repeater" unless "Simplex=On"
        # Set it ON for simplex channels, and it will have zero
        # effect because it only makes a difference on split channels
        "Through Mode": OFF if abs(channel.offset) > 0 else ON,
        # TODO: Support group list
    }
    if channel.talkgroup:
        d.update(Talkgroup_to_channel_detail(channel.talkgroup))
    return d


def Channel_to_dict(index, channel, codeplug):
    d = {
        "No.": str(index + 1),
        "Channel Name": channel.short_name,
        "Receive Frequency": format_frequency(channel.frequency),
        "Transmit Frequency": format_frequency(channel.frequency + channel.offset),
        "Channel Type": format_channel_type(type(channel)),
        "Transmit Power": str(channel.power),
        "Band Width": channel.bandwidth.flattened([Bandwidth._25, Bandwidth._125]).value + "K",
        "PTT Prohibit": value_replacements[channel.rx_only],
        "Scan List": channel.scanlist_name(codeplug),
    }
    if isinstance(channel, AnalogChannel):
        d.update(AnalogChannel_to_dict(channel))
    else:
        d.update(DigitalChannel_to_dict(channel))
    return d


def Zone_to_dict(index, zone, expand_members):
    d = {
        "No.": str(index + 1),
        "Zone Name": zone.name,
    }
    d.update(
        format_member_list(
            members=zone.unique_channels,
            list_name="Zone Channel Member",
            expand_members=expand_members,
        )
    )
    for list_name in ("A Channel", "B Channel"):
        d.update(
            format_member_list(
                members=(zone.unique_channels[0],),
                list_name=list_name,
                expand_members=expand_members,
            )
        )
    return d


def ScanList_to_dict(index, scanlist, expand_members):
    d = {
        "No.": str(index + 1),
        "Scan List Name": scanlist.name,
    }
    d.update(
        format_member_list(
            members=scanlist.unique_channels[:SCANLIST_MAX],
            list_name="Scan Channel Member",
            expand_members=expand_members,
        )
    )
    return d


def Codeplug_to_anytone_csv(cp, output_dir, models=None):
    if models is None:
        models = tuple(DEFAULT_SUPPORTED_RADIOS)
    for model_id in models:
        radio_dir = Path(output_dir) / model_id
        radio_dir.mkdir(parents=True, exist_ok=True)
        model = SUPPORTED_RADIOS[model_id]
        # filter down to supported frequency ranges
        mcp = cp.filter(ranges=model["frequency_range"])
        with (radio_dir / model["talkgroup_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, model["talkgroup"])
            csvw.writeheader()
            for ix, tg in enumerate(
                uniquify_contacts(mcp.contacts, ignore_timeslot=True)
            ):
                csvw.writerow(Talkgroup_to_dict(ix, tg))
        with (radio_dir / model["channel_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["channel"].keys()))
            csvw.writeheader()
            for ix, channel in enumerate(mcp.channels):
                d = model["channel"].copy()
                d.update(Channel_to_dict(ix, channel, mcp))
                csvw.writerow(replace_field_names(remove_fields(d, model), model))
        with (radio_dir / model["zone_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["zone"].keys()))
            csvw.writeheader()
            for ix, zone in enumerate(mcp.zones):
                csvw.writerow(Zone_to_dict(ix, zone, model["expand_members"]))
        with (radio_dir / model["scanlist_filename"]).open("w", newline="") as f:
            csvw = csv.DictWriter(f, tuple(model["scanlist"].keys()))
            csvw.writeheader()
            for ix, sl in enumerate(mcp.scanlists):
                d = model["scanlist"].copy()
                d.update(ScanList_to_dict(ix, sl, model["expand_members"]))
                csvw.writerow(d)
        logger.info("Wrote Anytone %s CSV files to '%s'", model_id, radio_dir)
