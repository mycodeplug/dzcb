import json

import attr

from dzcb.model import AnalogChannel, Contact, DigitalChannel, GroupList, ScanList, Zone

value_replacements = {
    None: "None",
    False: "No",
    True: "Yes",
}

Contact_name_map = dict(
    name="Name",
    dmrid="CallID",
    kind="CallType"
}

def Contact_to_dict(c):
    d = dict(
        CallReceiveTone=False,
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
    return {
        GroupList_name_maps[k]: v
        for k, v in attr.asdict(g).items()
        if k in attr.fields_dict(GroupList)
    }

ScanList_name_maps = dict(
    name="Name",
    channels="Channel",
)

def ScanList_to_dict(s):
    d = dict(
        # Default settings
        PriorityChannel1="Selected",
        PriorityChannel2="Selected",
        PrioritySampleTime="750",
        SignallingHoldTime="500",
        TxDesignatedChannel="Selected",
    )
    d.update({
        ScanList_name_maps[k]: v
        for k, v in attr.asdict(s).items()
        if k in attr.fields_dict(ScanList)
    })
    return d


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
    bandwidth="Bandwidth",
    tone_encode="CtcssEncode",
    tone_decode="CtcssDecode",
)


def AnalogChannel_to_dict(c):
    d = DefaultChannel.copy()
    d.update({
        "ChannelMode": "Analog",
    })
    d.update({
        AnalogChannel_name_map[k]:  value_replacements.get(v, str(v))
        for k, v in attr.asdict(c).items()
        if k in attr.fields_dict(AnalogChannel)
    })
    return d


DigitalChannel_name_maps = dict(
    name="Name",
    frequency="RxFrequency",
    offset="TxFrequencyOffset",
    power="Power",
    bandwidth="Bandwidth",
    color_code="Color Code",
)


def DigitalChannel_to_dict(c):
    d = DefaultChannel.copy()
    d.update({
        "ChannelMode": "Digital",
        "RepeaterSlot": str(c.talkgroup.timeslot),
    })
    d.update({
        DigitalChannel_name_map[k]:  value_replacements.get(v, str(v))
        for k, v in attr.asdict(c).items()
        if k in attr.fields_dict(DigitalChannel)
    })
    return d


def Channel_to_dict(c):
    if isinstance(c, AnalogChannel):
        return AnalogChannel_to_dict(c)
    elif isinstance(c, DigitalChannel):
        return DigitalChannel_to_dict(c)
    raise ValueError("Unknown type: {}".format(c))


Zone_name_maps = dict(
    name="Name",
    channels_a="ChannelA",
    channels_b="ChannelB",
)

def Zone_to_dict(z):
    return {
        Zone_name_maps[k]: v
        for k, v in attr.asdict(z).items()
        if k in attr.fields_dict(Zone)
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
