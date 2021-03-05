"""
dmrconfig output filter

https://github.com/OpenRTX/dmrconfig
"""

import enum
from typing import Iterable, Any, Sequence, Tuple, Optional, Callable, Union, Dict

import attr

from dzcb import __version__
from dzcb.model import Bandwidth, Codeplug, Power, AnalogChannel, DigitalChannel


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

zone_limit = {
    Radio.D868: (1, 250),
    Radio.DMR6X2: (1, 250),
    Radio.RD5R: (1, 250),
    Radio.GD77: (1, 250),
    Radio.MD_380: (1, 250),
    Radio.MD_UV380: (1, 250),
}

scanlist_limit = {
    Radio.D868: (1, 250),
    Radio.DMR6X2: (1, 250),
    Radio.RD5R: None,
    Radio.GD77: (1, 64),
    Radio.MD_380: (1, 250),
    Radio.MD_UV380: (1, 250),
}

contact_limit = {
    Radio.D868: (1, 10000),
    Radio.DMR6X2: (1, 10000),
    Radio.RD5R: (1, 256),
    Radio.GD77: (1, 1024),
    Radio.MD_380: (1, 10000),
    Radio.MD_UV380: (1, 10000),
}

grouplist_limit = {
    Radio.D868: (1, 250),
    Radio.DMR6X2: (1, 250),
    Radio.RD5R: (1, 64),
    Radio.GD77: (1, 76),
    Radio.MD_380: (1, 250),
    Radio.MD_UV380: (1, 250),
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
    Radio.D868: {
        Power.HIGH: "High",
        Power.MED: "Mid",
        Power.LOW: "Low",
        Power.TURBO: "Turbo",
    },
    Radio.DMR6X2: {
        Power.HIGH: "High",
        Power.MED: "Mid",
        Power.LOW: "Low",
        Power.TURBO: "Turbo",
    },
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

power = {
    Radio.D868: {
        Power.HIGH: "High",
        Power.MED: "Mid",
        Power.LOW: "Low",
        Power.TURBO: "Turbo",
    },
    Radio.DMR6X2: {
        Power.HIGH: "High",
        Power.MED: "Mid",
        Power.LOW: "Low",
        Power.TURBO: "Turbo",
    },
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

bandwidth = {
    Radio.D868: {Bandwidth._125: "12.5", Bandwidth._25: "25"},
    Radio.DMR6X2: {Bandwidth._125: "12.5", Bandwidth._25: "25"},
    Radio.RD5R: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.GD77: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_380: {Power.HIGH: "High", Power.LOW: "Low"},
    Radio.MD_UV380: {Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
}

plus_minus = {
    True: "+",
    False: "-",
}


Range = Union[int, Tuple[int, int]]


def items_by_index(
    all_items: Iterable[Any], key: Optional[Callable] = None, offset: int = 0
) -> Dict[Any, int]:
    """
    Build a mapping of items to indexes in the all_items sequence.
    """
    return {
        key(item) if key else item: ix + offset for ix, item in enumerate(all_items)
    }


def items_to_range_tuples(
    items_by_index: Dict[Any, int],
    selected_items: Iterable[Any],
    key: Optional[Callable] = None,
) -> Sequence[Range]:
    """
    Return an sequence of indexes and range tuples - (start, enc) of selected_items within all_items
    """
    selected_ranges = []
    for selected_index in tuple(
        items_by_index[key(item) if key else item] for item in selected_items
    ):
        if not selected_ranges:
            selected_ranges.append(selected_index)
            continue
        low_index = previous_index = selected_ranges[-1]
        if isinstance(previous_index, tuple):
            low_index, previous_index = previous_index  # unpack range
        if previous_index + 1 == selected_index:
            # in range! yee haw
            selected_ranges[-1] = (low_index, selected_index)
        else:
            # skipped some
            selected_ranges.append(selected_index)
    return tuple(selected_ranges)


def offset_ranges(ranges: Sequence[Range], offset: int) -> Sequence[Range]:
    """Add offset to all values in ranges"""
    return tuple(
        tuple(rv + offset for rv in rng_or_ix)
        if isinstance(rng_or_ix, tuple)
        else rng_or_ix + offset
        for rng_or_ix in ranges
    )


def format_ranges(ranges: Sequence[Range]) -> str:
    return ",".join(
        "{}-{}".format(*r) if isinstance(r, tuple) else str(r) for r in ranges
    )


@attr.s
class CodeplugIndexLookup:
    codeplug = attr.ib(validator=attr.validators.instance_of(Codeplug))
    offset = attr.ib(default=0)
    contact = attr.ib()
    grouplist_id = attr.ib()
    scanlist_id = attr.ib()
    channel = attr.ib()

    @contact.default
    def _contact(self):
        return items_by_index(self.codeplug.contacts, offset=self.offset)

    @grouplist_id.default
    def _grouplist_id(self):
        return items_by_index(
            self.codeplug.grouplists, key=lambda gl: gl._id, offset=self.offset
        )

    @scanlist_id.default
    def _scanlist_id(self):
        return items_by_index(
            self.codeplug.scanlists, key=lambda sl: sl._id, offset=self.offset
        )

    @channel.default
    def _channel(self):
        return items_by_index(self.codeplug.channels, offset=self.offset)


@attr.s
class Table:
    codeplug = attr.ib(validator=attr.validators.instance_of(Codeplug))
    radio = attr.ib(default=Radio.D868, validator=attr.validators.instance_of(Radio))
    index = attr.ib(validator=attr.validators.instance_of(CodeplugIndexLookup))

    field_names = tuple()
    fmt = ""

    @index.default
    def _index_default(self):
        return CodeplugIndexLookup(codeplug=self.codeplug, offset=1)

    def docs(self, **replacements):
        return self.__doc__.format(**replacements).replace("    #", "#")

    def header(self):
        return self.fmt.format(**{k: k for k in self.field_names})

    def item_to_dict(self, ix, item):
        raise NotImplementedError

    def format_row(self, ix, item):
        return self.fmt.format(**self.item_to_dict(ix, item))

    def name_munge(self, name):
        return name[: name_limit[self.radio]].replace(" ", "_")

    @classmethod
    def evolve_from(cls, table):
        return cls(**attr.asdict(table, recurse=False))


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

    field_names = (
        "Analog",
        "Name",
        "Receive",
        "Transmit",
        "Power",
        "Scan",
        "TOT",
        "RO",
        "Admit",
        "Squelch",
        "RxTone",
        "TxTone",
        "Width",
    )
    fmt = "{Analog:6} {Name:16} {Receive:8} {Transmit:8} {Power:5} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Squelch:7} {RxTone:6} {TxTone:6} {Width}"

    def item_to_dict(self, index, ch):
        return dict(
            Analog=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.frequency + ch.offset,
            Power=ch.power.flattened(power[self.radio]).value,
            Scan=self.index.scanlist_id.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Free",
            Squelch="Normal",
            RxTone=ch.tone_decode or "-",
            TxTone=ch.tone_encode or "-",
            Width=ch.bandwidth.flattened(bandwidth[self.radio]).value,
        )


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
    """

    field_names = (
        "Digital",
        "Name",
        "Receive",
        "Transmit",
        "Power",
        "Scan",
        "TOT",
        "RO",
        "Admit",
        "Color",
        "Slot",
        "RxGL",
        "TxContact",
    )
    fmt = "{Digital:7} {Name:16} {Receive:8} {Transmit:8} {Power:5} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Color:5} {Slot:4} {RxGL:4} {TxContact}"

    def item_to_dict(self, index, ch):
        return dict(
            Digital=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.frequency + ch.offset,
            Power=ch.power.flattened(power[self.radio]).value,
            Scan=self.index.scanlist_id.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Color",
            Color=ch.color_code,
            Slot=ch.talkgroup.timeslot.value,
            RxGL=self.index.grouplist_id.get(ch.grouplist, "-"),
            TxContact=self.index.contact.get(ch.talkgroup, "-"),
        )


class ZoneTable(Table):
    """
    # Table of channel zones.
    # 1) Zone number: {zone_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of channels: numbers and ranges (N-M) separated by comma
    """

    field_names = ("Zone", "Name", "Channels")
    fmt = "{Zone:4} {Name:16} {Channels}"

    def item_to_dict(self, index, zone):
        return dict(
            Zone=index,
            Name=self.name_munge(zone.name),
            Channels=format_ranges(
                items_to_range_tuples(self.index.channel, zone.unique_channels),
            ),
        )


class ScanlistTable(Table):
    """
    # Table of scan lists.
    # 1) Scan list number: {scanlist_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) Priority channel 1: -, Curr or index
    # 4) Priority channel 2: -, Curr or index
    # 5) Designated transmit channel: Sel or Last
    # 6) List of channels: numbers and ranges (N-M) separated by comma
    """

    field_names = ("Scanlist", "Name", "PCh1", "PCh2", "TxCh", "Channels")
    fmt = "{Scanlist:8} {Name:16} {PCh1:4} {PCh2:4} {TxCh:4} {Channels}"

    def item_to_dict(self, index, scanlist):
        return dict(
            Scanlist=index,
            Name=self.name_munge(scanlist.name),
            PCh1="Curr",
            PCh2="-",
            TxCh="Last",
            Channels=format_ranges(
                items_to_range_tuples(self.index.channel, scanlist.channels),
            ),
        )


class ContactsTable(Table):
    """
    # Table of contacts.
    # 1) Contact number: {contact_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) Call type: Group, Private, All
    # 4) Call ID: 1...16777215
    # 5) Call receive tone: -, +
    """

    field_names = ("Contact", "Name", "Type", "ID", "RxTone")
    fmt = "{Contact:8} {Name:16} {Type:7} {ID:8} {RxTone}"

    def item_to_dict(self, index, contact):
        return dict(
            Contact=index,
            Name=self.name_munge(contact.name),
            Type=contact.kind.value,
            ID=contact.dmrid,
            RxTone="-",
        )


class GrouplistTable(Table):
    """
    # Table of group lists.
    # 1) Group list number: {grouplist_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of contacts: numbers and ranges (N-M) separated by comma
    """

    field_names = ("Grouplist", "Name", "Contacts")
    fmt = "{Grouplist:10} {Name:16} {Contacts}"

    def item_to_dict(self, index, grouplist):
        return dict(
            Grouplist=index,
            Name=self.name_munge(grouplist.name),
            Contacts=format_ranges(
                items_to_range_tuples(self.index.contact, grouplist.contacts)
            ),
        )


def evolve_from_factory(table_type):
    def _evolve_from(self):
        return table_type.evolve_from(self.table)

    return attr.Factory(_evolve_from, takes_self=True)


@attr.s
class Dmrconfig_Codeplug:
    radio = attr.ib(validator=attr.validators.instance_of(Radio))
    table = attr.ib(validator=attr.validators.instance_of(Table))
    digital = attr.ib(default=evolve_from_factory(DigitalChannelTable))
    analog = attr.ib(default=evolve_from_factory(AnalogChannelTable))
    zone = attr.ib(default=evolve_from_factory(ZoneTable))
    scanlist = attr.ib(default=evolve_from_factory(ScanlistTable))
    contact = attr.ib(default=evolve_from_factory(ContactsTable))
    grouplist = attr.ib(default=evolve_from_factory(GrouplistTable))

    def __str__(self):
        output = ["Written by dzcb.output.dmrconfig v. {}".format(__version__)]
        analog_table = [
            self.analog.docs(
                channel_limit=format_ranges([channel_limit[self.radio]]),
                name_limit=name_limit[self.radio],
                power=", ".join(p.value for p in power[self.radio]),
                bandwidth=", ".join(b.value for b in bandwidth[self.radio]),
            ),
            self.analog.header(),
        ]
        digital_table = [
            self.digital.docs(
                channel_limit=format_ranges([channel_limit[self.radio]]),
                name_limit=name_limit[self.radio],
                power=", ".join(p.value for p in power[self.radio]),
            ),
            self.digital.header(),
        ]
        for ix, ch in enumerate(self.table.codeplug.channels):
            if isinstance(ch, AnalogChannel):
                analog_table.append(self.analog.format_row(ix + 1, ch))
            if isinstance(ch, DigitalChannel) and ch.talkgroup is not None:
                digital_table.append(self.digital.format_row(ix + 1, ch))

        output.extend(analog_table)
        output.extend(digital_table)

        output.append(
            self.contact.docs(contact_limit=format_ranges([contact_limit[self.radio]]))
        )
        output.append(self.contact.header())
        for ix, contact in enumerate(self.table.codeplug.contacts):
            output.append(self.contact.format_row(ix + 1, contact))

        output.append(
            self.grouplist.docs(
                grouplist_limit=format_ranges([grouplist_limit[self.radio]])
            )
        )
        output.append(self.grouplist.header())
        for ix, grouplist in enumerate(self.table.codeplug.grouplists):
            output.append(self.grouplist.format_row(ix + 1, grouplist))

        output.append(
            self.scanlist.docs(
                scanlist_limit=format_ranges([scanlist_limit[self.radio]])
            )
        )
        output.append(self.scanlist.header())
        for ix, scanlist in enumerate(self.table.codeplug.scanlists):
            output.append(self.scanlist.format_row(ix + 1, scanlist))

        output.append(
            self.zone.docs(zone_limit=format_ranges([zone_limit[self.radio]]))
        )
        output.append(self.zone.header())
        for ix, zone in enumerate(self.table.codeplug.zones):
            output.append(self.zone.format_row(ix + 1, zone))

        return "\n".join(output)
