"""
dzcb.model - data model for codeplug objects
"""
import csv
import enum
import functools
import logging
import re

import attr

import dzcb.data
import dzcb.exceptions
import dzcb.munge
import dzcb.tone

# XXX: i hate this
NAME_MAX = 16

logger = logging.getLogger(__name__)


class ConvertibleEnum(enum.Enum):
    @classmethod
    def from_any(cls, v):
        """Passable as an attr converter."""
        if isinstance(v, cls):
            return v
        return cls(v)

    def __str__(self):
        return str(self.value)


class Timeslot(ConvertibleEnum):
    """
    DMR Tier II uses 2x30ms timeslots capable of carrying independent traffic.
    """

    ONE = 1
    TWO = 2

    @classmethod
    def from_any(cls, v):
        """Passable as an attr converter."""
        if isinstance(v, cls):
            return v
        return cls(int(v))


class ContactType(ConvertibleEnum):
    GROUP = "Group"
    PRIVATE = "Private"


@attr.s(eq=True, frozen=True)
class Contact:
    """
    A Digital Contact: group or private
    """

    _all_contacts_by_id = {}

    name = attr.ib(eq=True, converter=dzcb.munge.contact_name)
    dmrid = attr.ib(eq=True, order=True, converter=int)
    kind = attr.ib(
        eq=True,
        default=ContactType.GROUP,
        validator=attr.validators.instance_of(ContactType),
        converter=ContactType.from_any,
    )

    def __attrs_post_init__(self):
        all_contacts_by_id = type(self)._all_contacts_by_id
        existing_contact = all_contacts_by_id.get(self.dmrid, None)
        if existing_contact:
            raise dzcb.exceptions.DuplicateDmrID(
                msg="{} ({}): DMR ID already exists as {}".format(
                    self.name, self.dmrid, existing_contact.name
                ),
                existing_contact=existing_contact,
            )
        all_contacts_by_id[self.dmrid] = self


@attr.s(eq=True, frozen=True)
class Talkgroup(Contact):
    timeslot = attr.ib(
        eq=True,
        order=True,
        default=Timeslot.ONE,
        validator=attr.validators.instance_of(Timeslot),
        converter=Timeslot.from_any,
    )

    def __attrs_post_init__(self):
        try:
            super().__attrs_post_init__()
        except dzcb.exceptions.DuplicateDmrID as dup:
            if (
                isinstance(dup.existing_contact, type(self))
                and self.timeslot == dup.existing_contact.timeslot
            ):
                raise

    @property
    def name_with_timeslot(self):
        ts = str(self.timeslot)
        if self.name.endswith(ts) and not self.name.startswith("TAC"):
            name = self.name
        else:
            name = "{} {}".format(self.name, ts)
        return name

    @classmethod
    def from_contact(cls, contact, timeslot):
        fields = attr.asdict(contact)
        fields["timeslot"] = timeslot
        try:
            return cls(**fields)
        except dzcb.exceptions.DuplicateDmrID as dup:
            return dup.existing_contact  # return the talkgroup we already have


class Power(ConvertibleEnum):
    LOW = "Low"
    MED = "Medium"
    HIGH = "High"


@attr.s(frozen=True)
class Channel:
    """Common channel attributes"""

    # keep track of short names to avoid duplicate names
    _all_channels = {}
    _short_names = {}

    name = attr.ib(validator=attr.validators.instance_of(str))
    frequency = attr.ib(validator=attr.validators.instance_of(float), converter=float)
    offset = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(float)),
        converter=attr.converters.optional(float),
    )
    power = attr.ib(
        default=Power.HIGH,
        validator=attr.validators.instance_of(Power),
        converter=Power.from_any,
    )
    rx_only = attr.ib(
        default=False, validator=attr.validators.instance_of(bool), converter=bool
    )
    scanlist = attr.ib(default=None)
    code = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)),
    )

    def __attrs_post_init__(self):
        type(self)._all_channels[self.name] = self

    @property
    def short_name(self):
        """Generate a unique short name for this channel"""
        attempt = 0
        maybe_this_channel = None
        while maybe_this_channel != self:
            maybe_short_name = dzcb.munge.channel_name(
                self.name, NAME_MAX - (1 if attempt else 0)
            ) + (str(attempt) if attempt else "")
            maybe_this_channel = type(self)._short_names.setdefault(
                maybe_short_name, self
            )
            attempt += 1
            if attempt > 9:
                raise RuntimeError(
                    "Cannot find a non-conflicting channel short name for {}".format(
                        self
                    )
                )
        return maybe_short_name


def _tone_validator(instance, attribute, value):
    if value is not None and value not in dzcb.tone.VALID_TONES:
        raise ValueError(
            "field {!r} has unknown tone {!r}".format(attribute.name, value)
        )


def _tone_converter(value):
    if not isinstance(value, str):
        value = str(value)
    elif re.match("[0-9.]+", value):
        # normalize float values
        value = str(float(value))
    return value.upper()


@attr.s
class AnalogChannel(Channel):
    tone_encode = attr.ib(
        default=None,
        validator=_tone_validator,
        converter=attr.converters.optional(_tone_converter),
    )
    tone_decode = attr.ib(
        default=None,
        validator=_tone_validator,
        converter=attr.converters.optional(_tone_converter),
    )
    # configurable bandwidth for analog (technically should be enum)
    bandwidth = attr.ib(
        default=25,
        validator=attr.validators.instance_of(float),
        converter=float,
    )
    # configurable squelch for analog
    squelch = attr.ib(
        default=1,
        validator=attr.validators.instance_of(int),
        converter=int,
    )


@attr.s
class DigitalChannel(Channel):
    # fixed bandwidth for digital
    bandwidth = 12.5
    squelch = 0
    color_code = attr.ib(default=1)
    grouplist = attr.ib(default=None)
    talkgroup = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(Talkgroup)),
    )
    # a list of other static talkgroups, which form the basis of an RX/scan list
    static_talkgroups = attr.ib(factory=list)

    def from_talkgroups(self, talkgroups):
        """
        Return a channel per talkgroup based on this channel's settings
        """
        return [
            attr.evolve(
                self,
                name="{} {}".format(
                    tg.name_with_timeslot[: NAME_MAX - 4],
                    (self.code if self.code else self.name)[:3],
                ),
                talkgroup=tg,
                scanlist=self.short_name,
                static_talkgroups=[],
            )
            for tg in talkgroups
        ]

    @property
    def zone_name(self):
        maybe_code = "{} ".format(self.code) if self.code else ""
        name = "{}{}".format(maybe_code, self.name)
        return name
        # shorten names for channel display
        # for old, new in self.name_replacements.items():
        #    name = name.replace(old, new)
        # return name


@attr.s
class GroupList:
    """
    A GroupList specifies a set of contacts that will be received on the same
    channel.
    """

    name = attr.ib(validator=attr.validators.instance_of(str))
    contacts = attr.ib(factory=list)

    @classmethod
    def prune_missing_contacts(cls, grouplists, contacts):
        """
        Return a sequence of new GroupList objects containing only contacts in `contacts`
        and in the order specified in contacts
        """
        return [
            gl
            for gl in [
                attr.evolve(
                    gl, contacts=[ct for ct in contacts if ct.name in set(glct.name for glct in gl.contacts)]
                )
                for gl in grouplists
            ]
            if gl.contacts
        ]


@attr.s
class ScanList:
    """
    A ScanList specifies a set of channels that can be sequentially scanned.
    """

    name = attr.ib(validator=attr.validators.instance_of(str))
    channels = attr.ib(
        factory=list,
        validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)),
    )

    @classmethod
    def from_names(cls, name, channel_names):
        channels = []
        for cn in channel_names:
            # TODO: require method to be called with a set of available channels
            #       because the global list may contain channels that have already
            #       been pruned in the given codeplug
            channel = Channel._short_names.get(cn, Channel._all_channels.get(cn))
            if channel is None:
                logger.debug(
                    "ScanList {!r} references unknown channel {!r}, ignoring".format(
                        name,
                        cn,
                    )
                )
                continue
            channels.append(channel)
        return cls(name=name, channels=channels)

    @classmethod
    def prune_missing_channels(cls, scanlists, channels):
        """
        Return a sequence of new ScanList objects containing only channels in `channels`
        """
        channel_names = set(ch.name for ch in channels)
        return [
            sl
            for sl in [
                attr.evolve(
                    sl, channels=[ch for ch in sl.channels if ch.name in channel_names]
                )
                for sl in scanlists
            ]
            if sl.channels
        ]

    @property
    def unique_channels(self):
        return tuple(self.channels)


@attr.s
class Zone:
    """
    A Zone groups channels together by name
    """

    name = attr.ib(validator=attr.validators.instance_of(str))
    channels_a = attr.ib(
        factory=list,
        validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)),
    )
    channels_b = attr.ib(
        factory=list,
        validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)),
    )

    @classmethod
    def prune_missing_channels(cls, zones, channels):
        """
        Return a sequence of new Zone objects containing only channels in `channels`
        """

        def channel_order(zone):
            unique_channels = set(zch.name for zch in zone.unique_channels)
            zone_channels = [ch for ch in channels if ch.name in unique_channels]
            channels_a = set(zch.name for zch in zone.channels_a)
            channels_b = set(zch.name for zch in zone.channels_b)
            return attr.evolve(
                zone,
                channels_a=tuple(ch for ch in zone_channels if ch.name in channels_a),
                channels_b=tuple(ch for ch in zone_channels if ch.name in channels_b)
            )

        ordered_zones = tuple(channel_order(zn) for zn in zones)
        return [zn for zn in ordered_zones if zn.channels_a or zn.channels_b]

    @property
    def unique_channels(self):
        channels = list(self.channels_a)
        for ch in self.channels_b:
            if ch not in channels:
                channels.append(ch)
        return tuple(channels)


@attr.s
class Ordering:
    contacts = attr.ib(factory=list)
    channels = attr.ib(factory=list)
    grouplists = attr.ib(factory=list)
    scanlists = attr.ib(factory=list)
    zones = attr.ib(factory=list)

    @classmethod
    def from_csv(cls, ordering_csv):
        order = {}
        csvr = csv.DictReader(ordering_csv)
        for r in csvr:
            for obj, item in r.items():
                if not item:
                    continue
                order.setdefault(obj.lower(), []).append(item)
        return cls(**order)

    def __add__(self, other):
        if not isinstance(other, type(self)):
            return None
        return type(self)(
            **{
                attribute.name: getattr(self, attribute.name) + getattr(other, attribute.name)
                for attribute in attr.fields(type(self))
            }
        )


def uniquify_contacts(contacts):
    """
    Return a sequence of contacts with all duplicates removed.

    If any duplicate names are found without matching numbers, an exception is raised.
    """
    ctd = {}
    for ct in contacts:
        stored_ct = ctd.setdefault(ct.name, ct)
        if stored_ct.dmrid != ct.dmrid:
            raise RuntimeError(
                "Two contacts named {} have different IDs: {} {}".format(
                    ct.name, ct.dmrid, stored_ct.dmrid
                )
            )
    return tuple(ctd.values())


def filter_channel_frequency(channels, ranges):
    """
    :param channels: sequence of Channel to filter
    :param ranges: sequence of tuple of (low, high) frequency to retain
    :return: sequence of Channels within given ranges
    """
    if ranges is None:
        return channels

    def freq_in_range(freq):
        for low, high in ranges:
            if float(low) < freq < float(high):
                return True
        return False

    keep_channels = []
    channels_pruned = []

    for ch in channels:
        if freq_in_range(ch.frequency):
            keep_channels.append(ch)
            continue
        # none of the ranges matched, so prune this channel
        channels_pruned.append(ch)
    if channels_pruned:
        logger.info(
            "filter_channel_frequency: Excluding %s channels with frequency out of range: %s",
            len(channels_pruned),
            ranges,
        )
    return keep_channels


def _seq_items_repr(s):
    return "<{} items>".format(len(s))


@attr.s
class Codeplug:
    contacts = attr.ib(factory=tuple, converter=uniquify_contacts, repr=_seq_items_repr)
    channels = attr.ib(factory=tuple, converter=tuple, repr=_seq_items_repr)
    grouplists = attr.ib(factory=tuple, converter=tuple, repr=_seq_items_repr)
    scanlists = attr.ib(factory=tuple, converter=tuple, repr=_seq_items_repr)
    zones = attr.ib(factory=tuple, converter=tuple, repr=_seq_items_repr)

    def filter(
        self, include=None, exclude=None, order=None, reverse_order=None, ranges=None
    ):
        """
        Filter codeplug objects and return a new Codeplug.

        :param include: Ordering object of codeplug objects to retain
        :param exclude: Ordering object of codeplug objects to return
        :param order: Ordering object specifying top down order
        :param reverse_order: Ordering object specifying bottom up order
        :param ranges: Frequency ranges of channels to retain
        :return: New Codeplug with filtering applied
        """
        # create a mutable codeplug for sorting
        cp = dict(
            contacts=list(self.contacts),
            channels=filter_channel_frequency(self.channels, ranges),
            grouplists=list(self.grouplists),
            scanlists=list(self.scanlists),
            zones=list(self.zones),
        )

        def _filter_inplace(ordering, munge):
            """
            Filter ``cp`` in place according to the `ordering` object
            calling the munge function with the object list and matching
            ordering list for the object type.

            If the munge function mutates the object list, it should
            return None. Otherwise the return value is assigned back
            to the codeplug dict and is expected to be a list.
            """
            for obj_type, objects in cp.items():
                ordering_list = getattr(ordering, obj_type, None)
                if ordering_list:
                    munge_result = munge(objects, ordering_list)
                    if munge_result:
                        cp[obj_type] = munge_result

        # keep objects in the include list
        def _include_filter(objects, ordering_list):
            pats = tuple(re.compile(pat, flags=re.IGNORECASE) for pat in ordering_list)
            return [o for o in objects if any(p.match(o.name) for p in pats)]

        # keep objects not in the exclude list
        def _exclude_filter(objects, ordering_list):
            pats = tuple(re.compile(pat, flags=re.IGNORECASE) for pat in ordering_list)
            return [o for o in objects if not any(p.match(o.name) for p in pats)]

        # order and reverse order the objects
        def _order_filter(objects, ordering_list, reverse=False):
            return dzcb.munge.ordered_re(
                seq=objects,
                order_regexs=ordering_list,
                key=lambda o: o.name,
                reverse=reverse,
            )

        # order static_talkgroups based on contact order
        def order_static_talkgroups(ch):
            if isinstance(ch, AnalogChannel) or not ch.static_talkgroups:
                return ch
            static_talkgroup_names = [tg.name for tg in ch.static_talkgroups]
            return attr.evolve(
                ch,
                static_talkgroups=[
                    tg for tg in cp["contacts"] if tg.name in static_talkgroup_names
                ],
            )

        if include:
            _filter_inplace(include, _include_filter)
        if exclude:
            _filter_inplace(exclude, _exclude_filter)
        if order:
            _filter_inplace(order, _order_filter)
        if reverse_order:
            _filter_inplace(reverse_order, functools.partial(_order_filter, reverse=True))

        # Reorder static talkgroups and remove channels with missing talkgroups
        contact_names = set(tg.name for tg in cp["contacts"])

        def talkgroup_exists(ch):
            if isinstance(ch, AnalogChannel) or ch.talkgroup is None:
                return True
            return ch.talkgroup.name in contact_names

        cp["channels"] = [
            order_static_talkgroups(ch) for ch in cp["channels"] if talkgroup_exists(ch)
        ]

        # Prune orphan channels and contacts from containers
        # and reorder objects in containers according to their primary order
        cp["grouplists"] = GroupList.prune_missing_contacts(
            cp["grouplists"], cp["contacts"]
        )
        cp["scanlists"] = ScanList.prune_missing_channels(
            cp["scanlists"], cp["channels"]
        )
        cp["zones"] = Zone.prune_missing_channels(cp["zones"], cp["channels"])

        return attr.evolve(self, **cp)

    def replace_scanlists(self, scanlist_dicts):
        """
        Return a new codeplug with additional scanlists.

        If the scanlist name appears in the codeplug, the entire scanlist
        is replaced by the new definition.

        If any channel names are not present in the codeplug, those channels
        will be ignored.

        :param scanlist_dicts: dict of scanlist_name -> [channel_name1, channel_name2, ...]
        """
        scanlists = {sl.name: sl for sl in self.scanlists}
        for sl_name, channels in scanlist_dicts.items():
            scanlists[sl_name] = ScanList.from_names(
                name=sl_name, channel_names=channels
            )

        return attr.evolve(self, scanlists=scanlists.values())

    def expand_static_talkgroups(self, static_talkgroup_order=None):
        """
        This function replaces channels with static_talkgroups by a zone
        containing a channel per talkgroup in static_talkgroups.

        :return: new Codeplug with additional channels and zones for each
            DigitalChannel with static_talkgroups
        """
        if static_talkgroup_order is None:
            static_talkgroup_order = []
        zones = list(self.zones)
        channels = []
        exp_scanlists = []
        for ch in self.channels:
            if not isinstance(ch, DigitalChannel) or not ch.static_talkgroups:
                channels.append(ch)
                continue
            zone_channels = ch.from_talkgroups(
                ch.static_talkgroups,
            )
            zscanlist = ScanList(
                name=ch.short_name,
                channels=zone_channels,
            )
            exp_scanlists.append(zscanlist)
            zones.append(
                Zone(
                    name=ch.short_name,
                    channels_a=zone_channels,
                    channels_b=zone_channels,
                )
            )
            channels.extend(zone_channels)

        return attr.evolve(
            self,
            channels=channels,
            # Don't reference channels that no longer exist
            scanlists=ScanList.prune_missing_channels(self.scanlists, channels)
            + exp_scanlists,
            zones=Zone.prune_missing_channels(zones, channels),
        )
