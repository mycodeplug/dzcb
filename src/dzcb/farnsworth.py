import json

import attr

from dzcb.model import AnalogChannel, Contact, DigitalChannel, GroupList, ScanList, Zone
import dzcb.munge

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
    d.update({
        Contact_name_map[k]: value_replacements.get(v, str(v))
        for k, v in attr.asdict(c).items()
        if k in attr.fields_dict(Contact)
    })
    return d


GroupList_name_maps = dict(
    name="Name",
    contacts="Contact",
)

def GroupList_to_dict(g):
    d = {
        GroupList_name_maps[k]: v
        for k, v in attr.asdict(g).items()
        if k in attr.fields_dict(GroupList)
    }
    return d

def ScanList_to_dict(s):
    return dict(
        Name=dzcb.munge.zone_name(s.name, NAME_MAX),
        Channel=[
            dzcb.munge.channel_name(ch, NAME_MAX)
            for ch in s.channels
        ],
        # Default settings
        PriorityChannel1="Selected",
        PriorityChannel2="Selected",
        PrioritySampleTime="750",
        SignallingHoldTime="500",
        TxDesignatedChannel="Selected",
    )


DefaultChannel = dict(
    AdmitCriteria="Color code",
    AllowTalkaround=True,
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
    Tot=90,
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


def AnalogChannel_to_dict(c):
    d = DefaultChannel.copy()
    d.update({
        "ChannelMode": "Analog",
    })
    d.update({
        AnalogChannel_name_maps[k]: v
        for k, v in attr.asdict(c).items()
        if k in attr.fields_dict(AnalogChannel) and k in AnalogChannel_name_maps
    })
    d["Name"] = dzcb.munge.channel_name(d["Name"], NAME_MAX)
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
    color_code="Color Code",
)


def DigitalChannel_to_dict(c):
    d = DefaultChannel.copy()
    d.update({
        "ChannelMode": "Digital",
        "RepeaterSlot": str(c.talkgroup.timeslot) if c.talkgroup else 1,
        "ContactName": str(c.talkgroup.name) if c.talkgroup else "Parrot 1",
        "GroupList": str(c.grouplist.name) if c.grouplist else None,
        "ScanList": dzcb.munge.zone_name(
            str(c.scanlist.name),
            NAME_MAX,
        ) if c.scanlist else None,
    })
    d.update({
        DigitalChannel_name_maps[k]: v
        for k, v in attr.asdict(c).items()
        if k in attr.fields_dict(DigitalChannel) and k in DigitalChannel_name_maps
    })
    d["Name"] = dzcb.munge.channel_name(d["Name"], NAME_MAX)
    return d


Channel_value_replacements = {
    None: "None",
    False: "Off",
    True: "On",
}


def Channel_to_dict(c):
    d = None
    if isinstance(c, AnalogChannel):
        d = AnalogChannel_to_dict(c)
    elif isinstance(c, DigitalChannel):
        d = DigitalChannel_to_dict(c)
    if d is None:
        raise ValueError("Unknown type: {}".format(c))
    return {
        k: Channel_value_replacements.get(v, str(v))
        for k, v in d.items()
    }


def Zone_to_dict(z):
    return {
        "Name": dzcb.munge.zone_name(z.name, NAME_MAX),
        "ChannelA": [dzcb.munge.channel_name(ch, NAME_MAX) for ch in z.channels_a],
        "ChannelB": [dzcb.munge.channel_name(ch, NAME_MAX) for ch in z.channels_b],
    }


def Codeplug_to_json(cp, based_on=None):
    cp_dict = {}
    if based_on is not None:
        cp_dict = json.load(based_on)
    cp_dict.update(
        dict(
            Contacts=[Contact_to_dict(c) for c in cp.contacts],
            Channels=[Channel_to_dict(c) for c in cp.channels],
            GroupLists=[GroupList_to_dict(c) for c in cp.grouplists],
            ScanLists=[ScanList_to_dict(c) for c in cp.scanlists],
            Zones=[Zone_to_dict(c) for c in cp.zones],
        )
    )
    return json.dumps(cp_dict, indent=2)
