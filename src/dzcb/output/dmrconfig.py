"""
dmrconfig output filter

https://github.com/OpenRTX/dmrconfig
"""

import enum

import attr

from dzcb.model import Bandwidth, Codeplug, Power


class Radio(enum.Enum):
    D868 = "Anytone AT-D868UV"
    DMR6X2 = "BTECH DMR-6x2"
    GD77 = "Radioddity GD-77"
    MD_UV380 = "TYT MD-UV380"
    MD_380 = "TYT MD-380"
    RD5R = "Baofeng RD-5R"


channel_limit = {
    Radio.D868: (1, 4000),
    Radio.DMR6X2: (1, 4000),
    Radio.RD5R: (1, 1024),
    Radio.GD77: (1, 1024),
    Radio.MD_380: (1, 1000),
    Radio.MD_UV380: (1, 3000),
}

name_limit = {
    Radio.D868: 16,
    Radio.DMR6X2: 16,
    Radio.RD5R: 16,
    Radio.GD77: 16,
    Radio.MD_380: 16,
    Radio.MD_UV380: 16,
}

power = {
    Radio.D868: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low", Power.TURBO: "Turbo"},
    Radio.DMR6X2: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low", Power.TURBO: "Turbo"},
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

power = {
    Radio.D868: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low", Power.TURBO: "Turbo"},
    Radio.DMR6X2: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low", Power.TURBO: "Turbo"},
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

bandwidth = {
    Radio.D868: {Bandwidth._125: "12.5", Bandwidth._25: "25"}
    Radio.DMR6X2: {Bandwidth._125: "12.5", Bandwidth._25: "25"}
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

plus_minus = {
    True: "+",
    False: "-",
}


@attr.s
class Table:
    radio = attr.ib(validator=attr.validators.instance_of(Radio))
    codeplug = attr.ib(validator=attr.validators.instance_of(Codeplug))


@attr.s
class AnalogChannelTable(Table):
    """
    # Table of analog channels.
    # 1) Channel number: {channel_limit}
    # 2) Name: up to {name_limit} characters, use '_' instead of space
    # 3) Receive frequency in MHz
    # 4) Transmit frequency or +/- offset in MHz
    # 5) Transmit power: {power}
    # 6) Scan list: - or index
    # 7) Transmit timeout timer: (unused)
    # 8) Receive only: -, +
    # 9) Admit criteria: -, Free, Tone
    # 10) Squelch level: Normal (unused)
    # 11) Guard tone for receive, or '-' to disable
    # 12) Guard tone for transmit, or '-' to disable
    # 13) Bandwidth in kHz: {bandwidth}
    """
    field_names = ("Analog", "Name", "Receive", "Transmit", "Power", "Scan", "TOT", "RO", "Admit", "Squelch", "RxTone", "TxTone", "Width")

    def item_to_dict(self, index, ch):
        # XXX: If the scanlists are renamed via replacements,
        #      then the channels won't be able to find the corresponding scanlist
        #      Not the end of the world, but annoying
        scanlist_name_to_index = {
            sl.name: ix + 1 for ix, sl in enumerate(self.codeplug.scanlists)
        }

        return dict(
            Analog=index,
            Name=ch.short_name[:name_limit[self.radio]],
            Receive=ch.frequency,
            Transmit=ch.frequency + ch.offset,
            Power=ch.power.flattened(power[self.radio]).value,
            Scan=scanlist_name_to_index.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Free",
            Squelch="Normal",
            RxTone=ch.tone_decode or "-",
            TxTone=ch.tone_encode or "-",
            Width=ch.bandwidth.flattened(bandwidth[self.radio]).value,
        )


@attr.s
class DigitalChannelTable(Table):
    """
    # Table of digital channels.
    # 1) Channel number: {channel_limit}
    # 2) Name: up to {name_limit} characters, use '_' instead of space
    # 3) Receive frequency in MHz
    # 4) Transmit frequency or +/- offset in MHz
    # 5) Transmit power: {power}
    # 6) Scan list: - or index in Scanlist table
    # 7) Transmit timeout timer: (unused)
    # 8) Receive only: -, +
    # 9) Admit criteria: -, Free, Color, NColor
    # 10) Color code: 0, 1, 2, 3... 15
    # 11) Time slot: 1 or 2
    # 12) Receive group list: - or index in Grouplist table
    # 13) Contact for transmit: - or index in Contacts table
    Digital Name             Receive   Transmit Power Scan TOT RO Admit  Color Slot RxGL TxContact
    """
    field_names = ("Digital", "Name", "Receive", "Transmit", "Power", "Scan", "TOT", "RO", "Admit", "Color", "Slot", "RxGL", "TxContact")

    def item_to_dict(self, index, ch):
        # XXX: If the scanlists are renamed via replacements,
        #      then the channels won't be able to find the corresponding scanlist
        #      Not the end of the world, but annoying
        scanlist_name_to_index = {
            sl.name: ix + 1 for ix, sl in enumerate(self.codeplug.scanlists)
        }
        contact_to_index = {
            ct: ix + 1 for ix, ct in enumerate(self.codeplug.contacts)
        }
        grouplist_to_index = {
            gl: ix + 1 for ix, gl in enumerate(self.codeplug.grouplists)
        }

        return dict(
            Digital=index,
            Name=ch.short_name[:name_limit[self.radio]],
            Receive=ch.frequency,
            Transmit=ch.frequency + ch.offset,
            Power=ch.power.flattened(power[self.radio]).value,
            Scan=scanlist_name_to_index.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Color",
            Color=ch.color_code,
            Slot=ch.talkgroup.timeslot.value,
            RxGL=grouplist_to_index[ch.grouplist],
            TxContact=contact_to_index[ch.talkgroup],
        )


@attr.s
class Dmrconfig_Codeplug:
    radio = attr.ib(validator=attr.validators.instance_of(Radio))
    digital = attr.ib()
    analog = attr.ib()
    zone = attr.ib()
    scanlist = attr.ib()
    contact = attr.ib()
    grouplist = attr.ib()
    message = attr.ib()
    id = attr.ib()
    name = attr.ib()
    intro_line_1 = attr.ib()
    intro_line_2 = attr.ib()
