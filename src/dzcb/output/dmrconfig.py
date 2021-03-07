"""
dmrconfig output filter

https://github.com/OpenRTX/dmrconfig
"""

import datetime
import enum
import time
from typing import (
    Iterable,
    Any,
    Sequence,
    Tuple,
    Optional,
    Callable,
    Union,
    Dict,
    ClassVar,
)

import attr

from dzcb import __version__
from dzcb.model import Bandwidth, Codeplug, Power, AnalogChannel, DigitalChannel


@attr.s(frozen=True)
class RadioDetail:
    """
    Represents the differences between radio types.

    The most common values are presented as defaults to be overridden.
    """

    name = attr.ib(validator=attr.validators.instance_of(str))
    nchan = attr.ib(default=4000, validator=attr.validators.instance_of(int))
    ncontacts = attr.ib(default=10000, validator=attr.validators.instance_of(int))
    nzones = attr.ib(default=250, validator=attr.validators.instance_of(int))
    nglists = attr.ib(default=250, validator=attr.validators.instance_of(int))
    nscanl = attr.ib(default=250, validator=attr.validators.instance_of(int))
    name_limit = attr.ib(default=16, validator=attr.validators.instance_of(int))
    power = attr.ib(
        validator=attr.validators.deep_mapping(
            key_validator=attr.validators.instance_of(Power),
            value_validator=attr.validators.instance_of(str),
        )
    )
    bandwidth = attr.ib(
        validator=attr.validators.deep_mapping(
            key_validator=attr.validators.instance_of(Bandwidth),
            value_validator=attr.validators.instance_of(str),
        )
    )

    @power.default
    def _power_default(self):
        return {
            Power.HIGH: "High",
            Power.MED: "Mid",
            Power.LOW: "Low",
            Power.TURBO: "Turbo",
        }

    @bandwidth.default
    def _bandwidth_default(self):
        return {Bandwidth._125: "12.5", Bandwidth._25: "25"}


# https://github.com/OpenRTX/dmrconfig/blob/master/d868uv.c
_d868uv_c = RadioDetail(
    name="Anytone AT-D868UV",
)

# https://github.com/OpenRTX/dmrconfig/blob/master/dm1801.c
_dm1801_c = RadioDetail(
    name="Baofeng DM-1801",
    nchan=1024,
    ncontacts=1024,
    nzones=150,
    nglists=76,
    nscanl=64,
    power={Power.HIGH: "High", Power.LOW: "Low"},
)

# https://github.com/OpenRTX/dmrconfig/blob/master/gd77.c
_gd77_c = attr.evolve(_dm1801_c, name="Radioddity GD-77", nzones=250)

# https://github.com/OpenRTX/dmrconfig/blob/master/md380.c
_md380_c = RadioDetail(
    name="TYT MD-380",
    nchan=1000,
    ncontacts=1000,
    power={Power.HIGH: "High", Power.LOW: "Low"},
    bandwidth={Bandwidth._125: "12.5", Bandwidth._20: "20", Bandwidth._25: "25"},
)

# https://github.com/OpenRTX/dmrconfig/blob/master/rd5r.c
_rd5r_c = RadioDetail(
    name="Baofeng RD-5R",
    nchan=1024,
    ncontacts=256,
    nglists=64,
    power={Power.HIGH: "High", Power.LOW: "Low"},
)

# https://github.com/OpenRTX/dmrconfig/blob/master/ub380.c
_uv380_c = RadioDetail(
    name="TYT MD-UV380",
    nchan=3000,
    ncontacts=10000,
    power={Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
    bandwidth={Bandwidth._125: "12.5", Bandwidth._20: "20", Bandwidth._25: "25"},
)


class Radio(enum.Enum):
    """
    All supported radio types as of dmrconfig 1.1
    """

    D868UV = _d868uv_c
    D878UV = attr.evolve(
        _d868uv_c,
        name="Anytone AT-D878UV",
    )
    DMR6X2 = attr.evolve(
        _d868uv_c,
        name="BTECH DMR-6x2",
    )
    DM1801 = _dm1801_c
    GD77 = _gd77_c
    MD380 = _md380_c
    MD390 = attr.evolve(_md380_c, name="TYT MD-390")
    D900 = attr.evolve(_md380_c, name="Zastone D900")
    DP880 = attr.evolve(_md380_c, name="Zastone DP880")
    RT27D = attr.evolve(_md380_c, name="Radtel RT-27D")
    RD5R = _rd5r_c
    UV380 = _uv380_c
    UV390 = attr.evolve(_uv380_c, name="TYT MD-UV390")
    MD2017 = attr.evolve(_uv380_c, name="TYT MD-2017")
    MD9600 = attr.evolve(_uv380_c, name="TYT MD-9600")
    RT84 = attr.evolve(_uv380_c, name="Retevis RT84")

    @classmethod
    def from_name(cls, name):
        for radio in cls.__members__.values():
            if radio.value.name == name:
                return radio
        raise TypeError("Unknown name {!r}".format(name))


plus_minus = {
    True: "+",
    False: "-",
    "+": True,
    "-": False,
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
    radio = attr.ib(default=Radio.D868UV, validator=attr.validators.instance_of(Radio))
    index = attr.ib(validator=attr.validators.instance_of(CodeplugIndexLookup))
    include_docs = attr.ib(default=True, validator=attr.validators.instance_of(bool))

    object_name = ""
    field_names = tuple()
    fmt = ""

    @index.default
    def _index_default(self):
        return CodeplugIndexLookup(codeplug=self.codeplug, offset=1)

    def docs(self, **replacements):
        return self.__doc__.rstrip().format(**replacements).replace("    #", "#")

    def header(self):
        return self.fmt.format(**{k: k for k in self.field_names})

    def render(self):
        output = []
        if self.include_docs:
            output.append(self.docs())
        output.append(self.header())
        output.extend(self)
        return tuple(output)

    def item_to_dict(self, ix, item):
        raise NotImplementedError

    def format_row(self, ix, item):
        return self.fmt.format(**self.item_to_dict(ix, item))

    def name_munge(self, name):
        return name[: self.radio.value.name_limit].replace(" ", "_")

    @classmethod
    def evolve_from(cls, table, **kwargs):
        tdict = attr.asdict(table, recurse=False)
        tdict.update(kwargs)
        return cls(**tdict)

    def __iter__(self):
        if not self.object_name:
            raise NotImplementedError("No object_name specified for {!r}".format(self))
        for ix, item in enumerate(getattr(self.codeplug, self.object_name)):
            yield self.format_row(ix + 1, item)


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
    fmt = "{Analog:6} {Name:16} {Receive:8} {Transmit:8} {Power:6} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Squelch:7} {RxTone:6} {TxTone:6} {Width}"

    def item_to_dict(self, index, ch):
        return dict(
            Analog=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.transmit_frequency,
            Power=ch.power.flattened(self.radio.value.power).value,
            Scan=self.index.scanlist_id.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Free",
            Squelch="Normal",
            RxTone=ch.tone_decode or "-",
            TxTone=ch.tone_encode or "-",
            Width=ch.bandwidth.flattened(self.radio.value.bandwidth).value,
        )

    def docs(self):
        detail = self.radio.value
        return super().docs(
            channel_limit=f"1-{detail.nchan}",
            name_limit=detail.name_limit,
            power=", ".join(p.value for p in detail.power),
            bandwidth=", ".join(b.value for b in detail.bandwidth),
        )

    def __iter__(self):
        for ix, ch in enumerate(self.codeplug.channels):
            if not isinstance(ch, AnalogChannel):
                continue
            yield self.format_row(ix + 1, ch)


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
    fmt = "{Digital:7} {Name:16} {Receive:8} {Transmit:8} {Power:6} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Color:5} {Slot:4} {RxGL:4} {TxContact:5}"

    def item_to_dict(self, index, ch):
        tx_contact = "-"
        if ch.talkgroup:
            tx_contact = "{index:5}   # {name}".format(
                index=self.index.contact[ch.talkgroup],
                name=ch.talkgroup.name,
            )
        return dict(
            Digital=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.transmit_frequency,
            Power=ch.power.flattened(self.radio.value.power).value,
            Scan=self.index.scanlist_id.get(ch.scanlist, "-"),
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Color",
            Color=ch.color_code,
            Slot=ch.talkgroup.timeslot.value,
            RxGL=self.index.grouplist_id.get(ch.grouplist, "-"),
            TxContact=tx_contact,
        )

    def docs(self):
        detail = self.radio.value
        return super().docs(
            channel_limit=f"1-{detail.nchan}",
            name_limit=detail.name_limit,
            power=", ".join(p.value for p in detail.power),
        )

    def __iter__(self):
        for ix, ch in enumerate(self.codeplug.channels):
            if not isinstance(ch, DigitalChannel) or ch.talkgroup is None:
                continue
            yield self.format_row(ix + 1, ch)


class ZoneTable(Table):
    """
    # Table of channel zones.
    # 1) Zone number: {zone_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of channels: numbers and ranges (N-M) separated by comma
    """

    object_name = "zones"
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

    def docs(self):
        return super().docs(zone_limit=f"1-{self.radio.value.nzones}")


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

    object_name = "scanlists"
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

    def docs(self):
        return super().docs(scanlist_limit=f"1-{self.radio.value.nscanl}")


class ContactsTable(Table):
    """
    # Table of contacts.
    # 1) Contact number: {contact_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) Call type: Group, Private, All
    # 4) Call ID: 1...16777215
    # 5) Call receive tone: -, +
    """

    object_name = "contacts"
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

    def docs(self):
        return super().docs(contact_limit=f"1-{self.radio.value.ncontacts}")


class GrouplistTable(Table):
    """
    # Table of group lists.
    # 1) Group list number: {grouplist_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of contacts: numbers and ranges (N-M) separated by comma
    """

    object_name = "grouplists"
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

    def docs(self):
        return super().docs(
            grouplist_limit=f"1-{self.radio.value.nglists}",
        )


class TemplateError(ValueError):
    pass


@attr.s
class DmrConfigTemplate:
    header = attr.ib(factory=list)
    footer = attr.ib(factory=list)
    radio = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(Radio)),
    )
    ranges = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.deep_iterable(tuple, tuple))
    )
    include_docs = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(bool))
    )

    _header_lines = (
        "last programmed date",
        "cps software version",
    )

    _template_variables = {
        "$DATE": lambda: time.strftime("%Y-%m-%d"),
        "$ISODATE": lambda: datetime.datetime.now().isoformat(),
        "$TIME": lambda: time.strftime("%H:%M"),
        "$SECTIME": lambda: time.strftime("%H:%M:%S"),
    }

    @classmethod
    def _replace_variables(cls, line):
        for var, repl in cls._template_variables.items():
            if var in line:
                if callable(repl):
                    line = line.replace(var, repl())
                else:
                    line = line.replace(var, repl)
        return line

    @staticmethod
    def _parse_ranges(line):
        _, match, ranges = line.partition("!dzcb.ranges: ")
        if match:
            return tuple(
                rng.split("-", maxsplit=1)
                for rng in ranges.strip().split(",")
            )

    @staticmethod
    def _parse_radio(line):
        _, match, radio_type = line.partition("Radio: ")
        if match:
            return Radio.from_name(radio_type)

    @staticmethod
    def _parse_include_docs(line):
        _, match, include_docs = line.partition("!dzcb.include_docs:")
        if match:
            return plus_minus[include_docs.strip()]

    @classmethod
    def read_template(cls: ClassVar, template: str) -> ClassVar:
        """
        return DmrConfigTemplate

        raise TemplateError if template doesn't contain a valid "Radio: X" line
        """
        t = cls()
        for tline in template.splitlines():
            tline = cls._replace_variables(tline)
            if t.ranges is None:
                t.ranges = cls._parse_ranges(tline)
            if t.include_docs is None:
                t.include_docs = cls._parse_include_docs(tline)
            if t.radio is None:
                t.header.append(tline)
                t.radio = cls._parse_radio(tline)
            elif any(l in tline.lower() for l in cls._header_lines):
                t.header.append(tline)
            else:
                t.footer.append(tline)
        if t.radio is None:
            raise TemplateError("template should specify a radio type")
        t.header.append("")  # add a blank line before the generated content
        return t


def evolve_from_factory(table_type):
    """
    Responsible for applying template values to the passed in Table
    when creating subtables in Dmrconfig_Codeplug
    """
    def _evolve_from(self):
        template_fields = {}
        if self.template:
            if self.template.ranges:
                # ranges are expensive and require rewriting the codeplug and index
                # we only want to apply range filtering once per template
                self.table = attr.evolve(
                    self.table,
                    codeplug=self.table.codeplug.filter(ranges=self.template.ranges),
                    index=attr.NOTHING,  # rebuild index
                )
                self.template.ranges = None  # only apply once
            if self.template.radio:
                template_fields["radio"] = self.template.radio
            if self.template.include_docs is not None:
                template_fields["include_docs"] = self.template.include_docs
        return table_type.evolve_from(self.table, **template_fields)

    return attr.Factory(_evolve_from, takes_self=True)


@attr.s
class Dmrconfig_Codeplug:
    """
    A template should be a dmrconfig file with the analog, digital,
    contacts, groupslists, and scanlists removed. These will be
    filled in from the dzcb.model.Codeplug in the Table.
    """

    table = attr.ib(validator=attr.validators.instance_of(Table))
    template = attr.ib(
        default=None,
        converter=attr.converters.optional(DmrConfigTemplate.read_template),
    )
    digital = attr.ib(default=evolve_from_factory(DigitalChannelTable))
    analog = attr.ib(default=evolve_from_factory(AnalogChannelTable))
    zone = attr.ib(default=evolve_from_factory(ZoneTable))
    scanlist = attr.ib(default=evolve_from_factory(ScanlistTable))
    contact = attr.ib(default=evolve_from_factory(ContactsTable))
    grouplist = attr.ib(default=evolve_from_factory(GrouplistTable))

    def render_template(self):
        return "\n".join(
            tuple(self.template.header) + self.render() + tuple(self.template.footer),
        )

    def render(self):
        return (
            ("# Written by dzcb.output.dmrconfig v. {}".format(__version__),)
            + self.analog.render()
            + self.digital.render()
            + self.contact.render()
            + self.grouplist.render()
            + self.scanlist.render()
            + self.zone.render()
        )
