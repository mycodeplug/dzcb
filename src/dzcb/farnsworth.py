import json
import logging
import time

import attr

from dzcb.model import (
    AnalogChannel,
    Contact,
    DigitalChannel,
    GroupList,
    uniquify_contacts,
)
import dzcb.munge

logger = logging.getLogger(__name__)

NAME_MAX = 16

value_replacements = {
    None: "None",
    False: "No",
    True: "Yes",
}

Contact_name_map = dict(
    name="Name",
    dmrid="CallID",
    kind="CallType",
)


def Contact_to_dict(c):
    d = dict(
        CallReceiveTone="No",
    )
    d.update(
        {
            Contact_name_map[k]: value_replacements.get(v, str(v))
            for k, v in attr.asdict(c).items()
            if k in attr.fields_dict(Contact)
        }
    )
    return d


GroupList_name_maps = dict(
    name="Name",
    contacts="Contact",
)


def GroupList_to_dict(g, contacts_by_id):
    return {
        "Name": g.name,
        "Contact": [
            contacts_by_id.get(tg.dmrid, tg).name
            for tg in g.contacts
        ],
    }


def ScanList_to_dict(s):
    return dict(
        Name=dzcb.munge.zone_name(s.name, NAME_MAX),
        Channel=[ch.short_name for ch in s.channels],
        # Default settings
        PriorityChannel1="Selected",
        PriorityChannel2="None",
        PrioritySampleTime="2000",
        SignallingHoldTime="200",
        TxDesignatedChannel="Last Active Channel",
    )


DefaultChannel = dict(
    AdmitCriteria="Color code",
    AllowTalkaround=False,
    Autoscan=False,
    ColorCode=1,
    ContactName=None,
    CtcssDecode=None,
    CtcssEncode=None,
    DCDMSwitch=False,
    DataCallConfirmed=False,
    Decode1=False,
    Decode2=False,
    Decode3=False,
    Decode4=False,
    Decode5=False,
    Decode6=False,
    Decode7=False,
    Decode8=False,
    DisplayPTTID=False,
    EmergencyAlarmAck=False,
    EmergencySystem=None,
    GPSSystem=None,
    GroupList=None,
    InCallCriteria="Follow Admit Criteria",
    LeaderMS=False,
    LoneWorker=False,
    Privacy=None,
    PrivacyNumber=1,
    PrivateCallConfirmed=False,
    QtReverse=180,
    ReceiveGPSInfo=False,
    RepeaterSlot=1,
    ReverseBurst=False,
    RxOnly=False,
    RxRefFrequency="Medium",
    RxSignallingSystem=False,
    ScanList=None,
    SendGPSInfo=False,
    Squelch=0,
    Talkaround=False,
    Tot=120,
    TotRekeyDelay=0,
    TxRefFrequency="Medium",
    TxSignallingSystem=False,
    Vox=False,
)

AnalogChannel_name_maps = dict(
    name="Name",
    frequency="RxFrequency",
    offset="TxFrequencyOffset",
    power="Power",
    rx_only="RxOnly",
    bandwidth="Bandwidth",
    squelch="Squelch",
    tone_encode="CtcssEncode",
    tone_decode="CtcssDecode",
)


def AnalogChannel_to_dict(c, codeplug):
    d = DefaultChannel.copy()
    d.update(
        {
            "ChannelMode": "Analog",
            "Bandwidth": c.bandwidth.value,
            "ScanList": dzcb.munge.zone_name(c.scanlist_name(codeplug), NAME_MAX),
        }
    )
    d.update(
        {
            AnalogChannel_name_maps[k]: v
            for k, v in attr.asdict(c).items()
            if k in attr.fields_dict(AnalogChannel) and k in AnalogChannel_name_maps
        }
    )
    d["Name"] = c.short_name
    if d["CtcssEncode"]:
        if d["CtcssEncode"].startswith("D"):
            d["CtcssEncode"] += "N"
    else:
        d["CtcssEncode"] = "None"
    if d["CtcssDecode"]:
        if d["CtcssDecode"].startswith("D"):
            d["CtcssDecode"] += "N"
    else:
        d["CtcssDecode"] = "None"
    return d


DigitalChannel_name_maps = dict(
    name="Name",
    frequency="RxFrequency",
    offset="TxFrequencyOffset",
    power="Power",
    rx_only="RxOnly",
    bandwidth="Bandwidth",
    color_code="ColorCode",
)


def DigitalChannel_to_dict(c, codeplug, contacts_by_id):
    d = DefaultChannel.copy()
    talkgroup_name = "Parrot 1"
    if c.talkgroup:
        # get the dedupe'd contact's name for the given ID
        talkgroup_name = str(contacts_by_id.get(c.talkgroup.dmrid, c.talkgroup).name)
    d.update(
        {
            "ChannelMode": "Digital",
            "RepeaterSlot": str(c.talkgroup.timeslot) if c.talkgroup else 1,
            "ContactName": talkgroup_name,
            "GroupList": str(c.grouplist_name(codeplug)) if c.grouplist else None,
            "ScanList": dzcb.munge.zone_name(c.scanlist_name(codeplug), NAME_MAX),
        }
    )
    d.update(
        {
            DigitalChannel_name_maps[k]: v
            for k, v in attr.asdict(c).items()
            if k in attr.fields_dict(DigitalChannel) and k in DigitalChannel_name_maps
        }
    )
    d["Name"] = c.short_name
    return d


Channel_value_replacements = {
    None: "None",
    False: "Off",
    True: "On",
}


def Channel_to_dict(c, codeplug, contacts_by_id):
    d = None
    if isinstance(c, AnalogChannel):
        d = AnalogChannel_to_dict(c, codeplug)
    elif isinstance(c, DigitalChannel):
        d = DigitalChannel_to_dict(c, codeplug, contacts_by_id)
    if d is None:
        raise ValueError("Unknown type: {}".format(c))
    return {k: Channel_value_replacements.get(v, str(v)) for k, v in d.items()}


def Zone_to_dict(z):
    return {
        "Name": dzcb.munge.zone_name(z.name, NAME_MAX),
        "ChannelA": [ch.short_name for ch in z.channels_a],
        "ChannelB": [ch.short_name for ch in z.channels_b],
    }


def Codeplug_to_json(cp, based_on=None):
    cp_dict = {}
    if based_on is not None:
        if hasattr(based_on, "read"):
            cp_dict = json.load(based_on)
        else:
            cp_dict = json.loads(based_on)
    # determine supported frequency range from BasicInformation
    ranges = []
    basic_info = cp_dict.get("BasicInformation", {})
    if "LowFrequency" in basic_info:
        ranges.append((basic_info["LowFrequency"], basic_info["HighFrequency"]))
    elif "LowFrequencyA" in basic_info:
        ranges.append((basic_info["LowFrequencyA"], basic_info["HighFrequencyA"]))
        ranges.append((basic_info["LowFrequencyB"], basic_info["HighFrequencyB"]))
    if ranges:
        cp = cp.filter(ranges=ranges)
    contacts_by_id = {
        c.dmrid: c
        for c in uniquify_contacts(cp.contacts, ignore_timeslot=True)
    }
    cp_dict.update(
        dict(
            Contacts=[Contact_to_dict(c) for c in contacts_by_id.values()],
            Channels=[Channel_to_dict(c, cp, contacts_by_id) for c in cp.channels],
            GroupLists=[GroupList_to_dict(c, contacts_by_id) for c in cp.grouplists],
            ScanLists=[ScanList_to_dict(c) for c in cp.scanlists],
            Zones=[Zone_to_dict(c) for c in cp.zones],
        )
    )
    # Set the programming date in intro text
    general_settings = cp_dict.setdefault("GeneralSettings", {})
    if general_settings.get("IntroScreenLine1", None) == "$DATE":
        general_settings["IntroScreenLine1"] = time.strftime("%Y-%m-%d")
    logger.info(
        "Assemble JSON for %s",
        basic_info.get("Model", "Unknown. (probably won't work!)"),
    )
    return json.dumps(cp_dict, indent=2)
