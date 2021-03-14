"""
dmrconfig output filter

https://github.com/OpenRTX/dmrconfig
"""

import datetime
import enum
import logging
import re
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
import dzcb.munge
from dzcb.model import (
    Bandwidth,
    Codeplug,
    Power,
    AnalogChannel,
    DigitalChannel,
)


logger = logging.getLogger(__name__)


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
    zone_has_ab = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    n_zone_channels = attr.ib(default=16, validator=attr.validators.instance_of(int))
    n_scanlist_channels = attr.ib(
        default=32, validator=attr.validators.instance_of(int)
    )
    n_grouplist_contacts = attr.ib(
        default=32, validator=attr.validators.instance_of(int)
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

    def limit(self, object_type):
        if object_type == "channels":
            return self.nchan
        if object_type == "contacts":
            return self.ncontacts
        if object_type == "scanlists":
            return self.nscanl
        if object_type == "grouplists":
            return self.nglists
        if object_type == "zones":
            return self.nzones


# https://github.com/OpenRTX/dmrconfig/blob/master/d868uv.c
_d868uv_c = RadioDetail(
    name="Anytone AT-D868UV",
    n_zone_channels=250,
    n_scanlist_channels=50,
    n_grouplist_contacts=64,
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
    n_zone_channels=32,
)

# https://github.com/OpenRTX/dmrconfig/blob/master/gd77.c
_gd77_c = attr.evolve(
    _dm1801_c,
    name="Radioddity GD-77",
    nzones=250,
    n_zone_channels=16,
    n_scanlist_channels=31,
)

# https://github.com/OpenRTX/dmrconfig/blob/master/md380.c
_md380_c = RadioDetail(
    name="TYT MD-380",
    nchan=1000,
    ncontacts=1000,
    power={Power.HIGH: "High", Power.LOW: "Low"},
    bandwidth={Bandwidth._125: "12.5", Bandwidth._20: "20", Bandwidth._25: "25"},
    n_scanlist_channels=31,
)

# https://github.com/OpenRTX/dmrconfig/blob/master/rd5r.c
_rd5r_c = RadioDetail(
    name="Baofeng RD-5R",
    nchan=1024,
    ncontacts=256,
    nglists=64,
    power={Power.HIGH: "High", Power.LOW: "Low"},
    n_grouplist_contacts=16,
)

# https://github.com/OpenRTX/dmrconfig/blob/master/ub380.c
_uv380_c = RadioDetail(
    name="TYT MD-UV380",
    nchan=3000,
    ncontacts=10000,
    power={Power.HIGH: "High", Power.MED: "Mid", Power.LOW: "Low"},
    bandwidth={Bandwidth._125: "12.5", Bandwidth._20: "20", Bandwidth._25: "25"},
    zone_has_ab=True,
    n_zone_channels=64,
    n_scanlist_channels=31,
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

    Sort of removing duplicates, i guess
    """
    ibb = {}
    ix = 0
    for item in all_items:
        k = key(item) if key else item
        ibb.setdefault(k, ix + offset)
        ix += 1
    return ibb


def items_to_range_tuples(
    items_by_index: Dict[Any, int],
    selected_items: Iterable[Any],
    key: Optional[Callable] = None,
    max_index: Optional[int] = None,
    max_count: Optional[int] = None,
) -> Sequence[Range]:
    """
    Return an sequence of indexes and range tuples - (start, enc) of selected_items within all_items
    """
    count = 0
    selected_ranges = []
    for selected_index in tuple(
        items_by_index[key(item) if key else item] for item in selected_items
    ):
        if max_index is not None and selected_index > max_index:
            # index out of range for radio type
            continue
        count += 1
        if count > max_count:
            break
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
    # split apart tuples of consecutive numbers
    exploded_ranges = []
    for rng in selected_ranges:
        if isinstance(rng, tuple) and (rng[1] - rng[0]) == 1:
            exploded_ranges.extend(rng)
        else:
            exploded_ranges.append(rng)
    return tuple(exploded_ranges)


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


def ranges_to_total_items(ranges: Sequence[Range]) -> int:
    total = 0
    for r in ranges:
        if isinstance(r, tuple):
            total += r[1] - r[0] + 1
        else:
            total += 1
    return total


@attr.s
class CodeplugIndexLookup:
    codeplug = attr.ib(validator=attr.validators.instance_of(Codeplug))
    radio = attr.ib(validator=attr.validators.instance_of(Radio))
    offset = attr.ib(default=0)
    contact = attr.ib(default=None, init=False)  # set by _contacts_filtered
    grouplist_id = attr.ib(init=False)
    scanlist_id = attr.ib(init=False)
    channel = attr.ib(default=None, init=False)  # set by _channels_filtered
    _contacts_filtered = attr.ib(init=False)
    _channels_filtered = attr.ib(init=False)

    @_contacts_filtered.default
    def _contacts_filtered_init(self):
        contacts_filtered = []
        contact_names = set()
        for contact in self.codeplug.contacts:
            if contact.name not in contact_names:
                contact_names.add(contact.name)
                contacts_filtered.append(contact)
        # contact index keys on contact name
        self.contact = items_by_index(
            contacts_filtered, key=lambda ct: ct.name, offset=self.offset
        )
        return contacts_filtered

    @_channels_filtered.default
    def _channels_filtered_init(self):
        """
        Reorder the channel list, preferring the zone order (if truncation would occur)
        """
        channels_filtered = self.codeplug.channels
        if len(channels_filtered) > self.radio.value.nchan:
            channels_filtered = dzcb.munge.ordered(
                channels_filtered, self._zone_channel_order()
            )
        self.channel = items_by_index(channels_filtered, offset=self.offset)
        return channels_filtered

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

    def _zone_channel_order(self):
        seen_channels = set()
        zone_channels = []
        for zone in self.codeplug.zones:
            for ch in zone.unique_channels:
                if ch in seen_channels:
                    continue  # only need to see each channel once
                if len(seen_channels) >= self.radio.value.nchan:
                    return zone_channels
                seen_channels.add(ch)
                zone_channels.append(ch)
        return zone_channels


@attr.s
class Table:
    codeplug = attr.ib(
        validator=attr.validators.instance_of(Codeplug),
    )
    radio = attr.ib(default=Radio.D868UV, validator=attr.validators.instance_of(Radio))
    index = attr.ib(validator=attr.validators.instance_of(CodeplugIndexLookup))
    include_docs = attr.ib(default=True, validator=attr.validators.instance_of(bool))

    object_name = ""
    field_names = tuple()
    fmt = ""

    @index.default
    def _index_default(self):
        return CodeplugIndexLookup(codeplug=self.codeplug, radio=self.radio, offset=1)

    def docs(self, **replacements):
        return self.__doc__.rstrip().format(**replacements).replace("    #", "#")

    def header(self):
        return self.fmt.format(**{k: k for k in self.field_names}).lstrip()

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
        item_dict = self.item_to_dict(ix, item)
        if item_dict:
            return self.fmt.format(**item_dict)

    def name_munge(self, name):
        return name[: self.radio.value.name_limit].replace(" ", "_")

    @classmethod
    def evolve_from(cls, table, **kwargs):
        tdict = attr.asdict(table, recurse=False)
        tdict.update(kwargs)
        return cls(**tdict)

    def iter_objects(self, object_list, object_limit=None):
        for ix, item in enumerate(object_list):
            if object_limit is not None and ix + 1 > object_limit:
                logger.debug(
                    "{0} table is full, ignoring {1} {0}".format(
                        type(item).__name__, len(object_list) - ix
                    )
                )
                break
            row = self.format_row(ix + 1, item)
            if row:
                yield row

    def __iter__(self):
        if not self.object_name:
            raise NotImplementedError("No object_name specified for {!r}".format(self))
        object_list = getattr(self.codeplug, self.object_name)
        object_limit = self.radio.value.limit(self.object_name)
        return self.iter_objects(object_list, object_limit=object_limit)


class ChannelTable(Table):
    """
    analog/digital shared routine
    """

    model_object_class = None  # either AnalogChannel or DigitalChannel

    def docs(self):
        detail = self.radio.value
        return super().docs(
            channel_limit=f"1-{detail.nchan}",
            name_limit=detail.name_limit,
            power=", ".join(p.value for p in detail.power),
            bandwidth=", ".join(b.value for b in detail.bandwidth),
        )

    def __iter__(self):
        for ix, ch in enumerate(self.index._channels_filtered):
            if not isinstance(ch, self.model_object_class):
                continue
            if ix + 1 > self.radio.value.nchan:
                logger.debug(
                    "Channel table is full, ignoring {} channels".format(
                        len(self.index._channels_filtered) - ix
                    )
                )
                break
            yield self.format_row(ix + 1, ch)

    def scanlist_ix(self, ch):
        scanlist_ix = self.index.scanlist_id.get(ch.scanlist, None)
        if scanlist_ix is None or scanlist_ix <= self.radio.value.nscanl:
            return scanlist_ix
        logger.debug(
            "Ignoring scanlist for channel {}, {} out of range".format(
                ch.name, scanlist_ix
            )
        )


class AnalogChannelTable(ChannelTable):
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

    model_object_class = AnalogChannel
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
    fmt = "{Analog:^6} {Name:16} {Receive:8} {Transmit:8} {Power:6} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Squelch:7} {RxTone:6} {TxTone:6} {Width}"

    def item_to_dict(self, index, ch):
        def normal_dcs(tone):
            if not tone:
                return "-"
            if tone.startswith("D"):
                return tone + "N"
            return tone

        return dict(
            Analog=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.transmit_frequency,
            Power=self.radio.value.power[ch.power.flattened(self.radio.value.power)],
            Scan=self.scanlist_ix(ch) or "-",
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Free",
            Squelch="Normal",
            RxTone=normal_dcs(ch.tone_decode),
            TxTone=normal_dcs(ch.tone_encode),
            Width=ch.bandwidth.flattened(self.radio.value.bandwidth).value,
        )


class DigitalChannelTable(ChannelTable):
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

    model_object_class = DigitalChannel
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
    fmt = "{Digital:^7} {Name:16} {Receive:8} {Transmit:8} {Power:6} {Scan:4} {TOT:3} {RO:2} {Admit:5} {Color:5} {Slot:4} {RxGL:4} {TxContact:5}"

    def grouplist_ix(self, ch):
        grouplist_ix = self.index.grouplist_id.get(ch.grouplist, None)
        if grouplist_ix is None or grouplist_ix <= self.radio.value.nglists:
            return grouplist_ix
        logger.debug(
            "Ignoring grouplist for channel {}, {} out of range".format(
                ch.name, grouplist_ix
            )
        )

    def tx_contact(self, ch):
        if ch.talkgroup:
            ct_index = self.index.contact[ch.talkgroup.name]
            if ct_index <= self.radio.value.ncontacts:
                return "{index:5}   # {name}".format(
                    index=ct_index,
                    name=ch.talkgroup.name,
                )
            logger.debug(
                "Ignoring contact for channel {}, contact {} {} out of range".format(
                    ch.name, ch.talkgroup.name, ct_index
                )
            )
        return "-"

    def item_to_dict(self, index, ch):
        return dict(
            Digital=index,
            Name=self.name_munge(ch.short_name),
            Receive=ch.frequency,
            Transmit=ch.transmit_frequency,
            Power=self.radio.value.power[ch.power.flattened(self.radio.value.power)],
            Scan=self.scanlist_ix(ch) or "-",
            TOT=90,  # TODO: how to expose this parameter
            RO=plus_minus[ch.rx_only],
            Admit="Color",
            Color=ch.color_code,
            Slot=ch.talkgroup.timeslot.value if ch.talkgroup else 1,
            RxGL=self.grouplist_ix(ch) or "-",
            TxContact=self.tx_contact(ch),
        )


class ZoneTable(Table):
    """
    # Table of channel zones.
    # 1) Zone number: {zone_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of channels: numbers and ranges (N-M) separated by comma
    """

    object_name = "zones"
    field_names = ("Zone", "Name", "Channels")
    fmt = "{Zone:^6} {Name:16} {Channels}"

    def channels(self, zone, channel_list):
        ch_index_limit = self.radio.value.nchan
        ch_max = self.radio.value.n_zone_channels
        channel_ranges = items_to_range_tuples(
            self.index.channel,
            channel_list,
            max_index=ch_index_limit,
            max_count=ch_max,
        )
        channels = format_ranges(channel_ranges)
        if not channels:
            return
        len_channels_in_range = ranges_to_total_items(channel_ranges)
        if len_channels_in_range < len(channel_list):
            logger.debug(
                "Pruned {} channels beyond limit ({}) from zone {}".format(
                    len(channel_list) - len_channels_in_range,
                    ch_max,
                    zone.name,
                )
            )
        return channels

    def item_to_dict(self, index, zone, attribute="unique_channels"):
        channels = self.channels(zone, channel_list=getattr(zone, attribute))
        if not channels:
            logger.debug("Ignoring empty zone {}".format(zone.name))
            return
        return dict(
            Zone=index,
            Name=self.name_munge(zone.name),
            Channels=channels,
        )

    def format_row(self, ix, item):
        zone_dicts = []
        if self.radio.value.zone_has_ab:
            for ab in ("a", "b"):
                zchs = self.item_to_dict(f"{ix}{ab}", item, f"channels_{ab}")
                if zchs:
                    zone_dicts.append(zchs)
        else:
            zchs = self.item_to_dict(ix, item)
            if zchs:
                zone_dicts.append(zchs)
        return "\n".join(self.fmt.format(**zone) for zone in zone_dicts)

    def docs(self):
        return super().docs(zone_limit=f"1-{self.radio.value.nzones}")


class ScanlistTable(Table):
    """
    # Table of scan lists.
    # 1) Scan list number: {scanlist_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) Priority channel 1: -, Sel or index
    # 4) Priority channel 2: -, Sel or index
    # 5) Designated transmit channel: Sel or Last
    # 6) List of channels: numbers and ranges (N-M) separated by comma
    """

    object_name = "scanlists"
    field_names = ("Scanlist", "Name", "PCh1", "PCh2", "TxCh", "Channels")
    fmt = "{Scanlist:^8} {Name:16} {PCh1:4} {PCh2:4} {TxCh:4} {Channels}"

    def channels(self, scanlist):
        ch_index_limit = self.radio.value.nchan
        ch_max = self.radio.value.n_scanlist_channels
        channel_ranges = items_to_range_tuples(
            self.index.channel,
            scanlist.channels,
            max_index=ch_index_limit,
            max_count=ch_max,
        )
        channels = format_ranges(channel_ranges)
        if not channels:
            return
        len_channels_in_range = ranges_to_total_items(channel_ranges)
        if len_channels_in_range < len(scanlist.channels):
            logger.debug(
                "Pruned {} channels beyond limit ({}) from scanlist {}".format(
                    len(scanlist.channels) - len_channels_in_range,
                    ch_max,
                    scanlist.name,
                )
            )
        return channels

    def item_to_dict(self, index, scanlist):
        channels = self.channels(scanlist)
        if not channels:
            logger.debug("Ignoring empty scanlist {}".format(scanlist.name))
            return
        return dict(
            Scanlist=index,
            Name=self.name_munge(scanlist.name),
            PCh1="Sel",
            PCh2="-",
            TxCh="Last",
            Channels=channels,
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
    fmt = "{Contact:^8} {Name:16} {Type:7} {ID:8} {RxTone}"

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

    def __iter__(self):
        return self.iter_objects(
            self.index._contacts_filtered,  # unique by name
            object_limit=self.radio.value.limit(self.object_name),
        )


class GrouplistTable(Table):
    """
    # Table of group lists.
    # 1) Group list number: {grouplist_limit}
    # 2) Name: up to 16 characters, use '_' instead of space
    # 3) List of contacts: numbers and ranges (N-M) separated by comma
    """

    object_name = "grouplists"
    field_names = ("Grouplist", "Name", "Contacts")
    fmt = "{Grouplist:^10} {Name:16} {Contacts}"

    def contacts(self, grouplist):
        ct_index_limit = self.radio.value.ncontacts
        ct_max = self.radio.value.n_grouplist_contacts
        contact_ranges = items_to_range_tuples(
            self.index.contact,
            grouplist.contacts,
            key=lambda ct: ct.name,
            max_index=ct_index_limit,
            max_count=ct_max,
        )
        contacts = format_ranges(contact_ranges)
        if not contacts:
            return
        len_contacts_in_range = ranges_to_total_items(contact_ranges)
        if len_contacts_in_range < len(grouplist.contacts):
            logger.debug(
                "Pruned {} contacts beyond limits ({}) from grouplist {}".format(
                    len(grouplist.contacts) - len_contacts_in_range,
                    ct_max,
                    grouplist.name,
                )
            )
        return contacts

    def item_to_dict(self, index, grouplist):
        contacts = self.contacts(grouplist)
        if not contacts:
            logger.debug("Ignoring empty grouplist {}".format(grouplist.name))
            return
        return dict(
            Grouplist=index,
            Name=self.name_munge(grouplist.name),
            Contacts=contacts,
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
        validator=attr.validators.optional(
            attr.validators.deep_iterable(
                attr.validators.instance_of(tuple), attr.validators.instance_of(tuple)
            )
        ),
    )
    include_docs = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(bool)),
    )
    include_version = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(bool)),
    )

    _header_lines = (
        "last programmed date",
        "cps software version",
    )

    _version_comment_prefix = "# Written by dzcb.output.dmrconfig"
    _version_comment_rex = re.compile("^" + _version_comment_prefix)
    version_comment_line = f"{_version_comment_prefix} dzcb-{__version__}"

    _template_variables = {
        "$DATE": lambda: time.strftime("%Y-%m-%d"),
        "$ISODATE": lambda: datetime.datetime.now().isoformat(),
        "$TIME": lambda: time.strftime("%H:%M"),
        "$SECTIME": lambda: time.strftime("%H:%M:%S"),
    }

    _remove_tables = ("Analog", "Digital", "Zone", "Scanlist", "Contact", "Grouplist")
    _known_tables = _remove_tables + ("Message",)
    _comment_rex = re.compile(r"^\s*#")
    _table_of_comment_rex = re.compile(r"^\s*# Table of", flags=re.IGNORECASE)
    _table_row_rex = re.compile(r"^\s+[0-9]+")

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
        _, match, ranges = line.partition("!dzcb.ranges:")
        if match:
            return tuple(
                rng.split("-", maxsplit=1) for rng in ranges.strip().split(",")
            )

    @staticmethod
    def _parse_include_docs(line):
        _, match, include_docs = line.partition("!dzcb.include_docs:")
        if match:
            return plus_minus[include_docs.strip()]

    @staticmethod
    def _parse_include_version(line):
        _, match, include_version = line.partition("!dzcb.include_version:")
        if match:
            return plus_minus[include_version.strip()]

    _directives = [
        "ranges",
        "include_docs",
        "include_version",
    ]

    def _parse_directives(self, line):
        for var in self._directives:
            if getattr(self, var) is not None:
                continue
            parse = getattr(self, f"_parse_{var}")
            setattr(self, var, parse(line))

    @staticmethod
    def _parse_radio(line):
        _, match, radio_type = line.partition("Radio: ")
        if match:
            return Radio.from_name(radio_type)

    @classmethod
    def read_template(cls: ClassVar, template: str) -> ClassVar:
        """
        return DmrConfigTemplate

        raise TemplateError if template doesn't contain a valid "Radio: X" line
        """
        if isinstance(template, cls):
            return template  # already a template, done

        consuming_table = dict(
            name=None,
            lines=[],
        )

        def save_line(line):
            consuming_table["lines"].append(line)

        def remove_preceding_blank():
            # if a preceding blank line was saved, remove it
            if not t.footer[-1]:
                del t.footer[-1]

        def keep_or_drop_table():
            if consuming_table["name"] is not None:
                if consuming_table["name"] not in cls._remove_tables:
                    t.footer.extend(consuming_table["lines"])
                else:
                    remove_preceding_blank()
                consuming_table["name"] = None
                consuming_table["lines"] = []

        t = cls()
        for tline in template.splitlines():
            tline = cls._replace_variables(tline)
            t._parse_directives(tline)
            if cls._version_comment_rex.match(tline):
                remove_preceding_blank()
                continue  # strip the version line, if present
            if t.radio is None:
                t.header.append(tline)
                t.radio = cls._parse_radio(tline)
            elif any(l in tline.lower() for l in cls._header_lines):
                t.header.append(tline)
            # parse (and remove) tables
            elif cls._table_of_comment_rex.match(tline):
                # table of X comment seen; if we're already consuming a table, dump it
                keep_or_drop_table()
                save_line(tline)
            elif (
                cls._comment_rex.match(tline) and consuming_table["lines"]
            ) or cls._table_row_rex.match(tline):
                # comment in the middle of a table or table row
                save_line(tline)
            elif any(tline.startswith(table_name) for table_name in cls._known_tables):
                # new table header is seen
                keep_or_drop_table()
                consuming_table["name"] = tline.strip().partition(" ")[0]
                save_line(tline)
            else:
                keep_or_drop_table()
                t.footer.append(tline)
        if t.radio is None:
            raise TemplateError("template should specify a radio type")
        return t


def evolve_from_factory(table_type):
    """
    Responsible for evolving the Table when creating subtables in Dmrconfig_Codeplug
    """

    def _evolve_from(self):
        return table_type.evolve_from(self.table)

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
        validator=attr.validators.optional(
            attr.validators.instance_of(DmrConfigTemplate)
        )
    )
    digital = attr.ib(default=evolve_from_factory(DigitalChannelTable))
    analog = attr.ib(default=evolve_from_factory(AnalogChannelTable))
    zone = attr.ib(default=evolve_from_factory(ZoneTable))
    scanlist = attr.ib(default=evolve_from_factory(ScanlistTable))
    contact = attr.ib(default=evolve_from_factory(ContactsTable))
    grouplist = attr.ib(default=evolve_from_factory(GrouplistTable))

    @classmethod
    def from_codeplug(cls, codeplug, template=None):
        table_params = {}
        if template is not None:
            template = DmrConfigTemplate.read_template(template)
            if template.ranges:
                codeplug = codeplug.filter(ranges=template.ranges)
            if template.radio:
                table_params["radio"] = template.radio
            if template.include_docs:
                table_params["include_docs"] = template.include_docs
        return cls(
            table=Table(
                codeplug=codeplug,
                **table_params,
            ),
            template=template,
        )

    def render_template(self):
        if not self.template:
            raise RuntimeError("no template is defined")
        return "\n".join(
            tuple(self.template.header)
            + (
                ("", self.template.version_comment_line)
                if self.template.include_version is not False
                else tuple()
            )
            + self.render()
            + tuple(self.template.footer)
        )

    def render(self):
        return (
            self.analog.render()
            + self.digital.render()
            + self.contact.render()
            + self.grouplist.render()
            + self.scanlist.render()
            + self.zone.render()
        )
