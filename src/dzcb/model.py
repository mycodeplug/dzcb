"""
dzcb.model - data model for codeplug objects
"""
import csv
import enum
import functools
import logging
import re
import uuid
import warnings

import attr

import dzcb.data
import dzcb.exceptions
import dzcb.munge
import dzcb.tone
from dzcb.util import unique_name

# XXX: i hate this
NAME_MAX = 16

logger = logging.getLogger(__name__)


def exclude_id(a, _):
    return not a.name == "_id"


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


@attr.s(frozen=True)
class Contact:
    """
    A Digital Contact: group or private
    """

    name = attr.ib(eq=False, converter=dzcb.munge.contact_name)
    dmrid = attr.ib(order=True, converter=int)
    kind = attr.ib(
        default=ContactType.GROUP,
        validator=attr.validators.instance_of(ContactType),
        converter=ContactType.from_any,
    )


@attr.s(frozen=True)
class Talkgroup(Contact):

    timeslot = attr.ib(
        order=True,
        default=Timeslot.ONE,
        validator=attr.validators.instance_of(Timeslot),
        converter=Timeslot.from_any,
    )

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
        fields = attr.asdict(contact, recurse=False)
        fields["timeslot"] = timeslot
        return cls(**fields)


@attr.s(frozen=True)
class GroupList:
    """
    A GroupList specifies a set of contacts that will be received on the same
    channel.
    """

    name = attr.ib(eq=False, validator=attr.validators.instance_of(str))
    contacts = attr.ib(
        factory=tuple,
        eq=False,
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(Contact),
            iterable_validator=attr.validators.instance_of(tuple),
        ),
        converter=tuple,
    )
    # stable id can track object across name and contents changes
    _id = attr.ib(factory=uuid.uuid4, repr=False)

    @classmethod
    def prune_missing_contacts(cls, grouplists, contacts):
        """
        Return a sequence of new GroupList objects containing only contacts in `contacts`
        and in the order specified in contacts
        """

        def contact_order(grouplist):
            gl_contacts = set(glct for glct in grouplist.contacts)
            return attr.evolve(
                grouplist,
                contacts=tuple(ct for ct in contacts if ct in gl_contacts),
            )

        ordered_groupslists = tuple(contact_order(gl) for gl in grouplists)
        return tuple(gl for gl in ordered_groupslists if gl.contacts)


class Power(ConvertibleEnum):
    LOW = "Low"
    MED = "Medium"
    HIGH = "High"
    TURBO = "Turbo"

    def flattened(self, allowed_powers):
        if self in allowed_powers:
            return self
        if self is self.MED:
            return self.LOW
        if self is self.TURBO:
            return self.HIGH
        if self is self.LOW:
            return self.HIGH
        if self is self.HIGH:
            return self.LOW
        raise ValueError(
            "No known powers are allowed {!r} from {!r}".format(self, allowed_powers)
        )

    @classmethod
    def from_any(cls, v):
        """Passable as an attr converter."""
        if isinstance(v, str):
            # use title case string
            v = v.title()
        return super(Power, cls).from_any(v)


class Bandwidth(ConvertibleEnum):
    _125 = "12.5"
    _20 = "20"
    _25 = "25"

    def flattened(self, allowed_bandwidths):
        if self in allowed_bandwidths:
            return self
        if self is self._20:
            return self._25
        raise ValueError(
            "No known bandwidths are allowed {!r} from {!r}".format(
                self, allowed_bandwidths
            )
        )


def round_frequency(freq, ndigits=5):
    return round(float(freq), ndigits)


@attr.s(frozen=True)
class Channel:
    """Common channel attributes"""

    name = attr.ib(eq=False, validator=attr.validators.instance_of(str))
    frequency = attr.ib(
        validator=attr.validators.instance_of(float), converter=round_frequency
    )
    offset = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(float)),
        converter=attr.converters.optional(round_frequency),
    )
    power = attr.ib(
        default=Power.HIGH,
        validator=attr.validators.instance_of(Power),
        converter=Power.from_any,
    )
    rx_only = attr.ib(
        default=False, validator=attr.validators.instance_of(bool), converter=bool
    )
    scanlist = attr.ib(
        eq=False,
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(uuid.UUID)),
        converter=lambda sl: sl._id if isinstance(sl, ScanList) else sl,
    )
    code = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)),
    )
    # dedupe_key is used to force unique channels,
    # even when the short name would overlap
    _dedup_key = attr.ib(default=0, repr=False)

    def scanlist_name(self, codeplug):
        if self.scanlist:
            return codeplug.lookup(self.scanlist).name

    @property
    def short_name(self):
        """Generate a short name for this channel"""
        suffix = str(self._dedup_key or "")
        return dzcb.munge.channel_name(self.name, NAME_MAX - len(suffix)) + suffix

    @property
    def transmit_frequency(self):
        offset = self.offset if self.offset else 0
        return round_frequency(self.frequency + offset)


def _tone_validator(instance, attribute, value):
    if value is not None and value not in dzcb.tone.VALID_TONES:
        message = "field {!r} for {} has unknown tone {!r}".format(
            attribute.name, instance.name, value
        )
        if dzcb.tone.REQUIRE_VALID_TONE:
            raise ValueError(message)
        else:
            logger.warning(message)


def _tone_converter(value):
    if not isinstance(value, str):
        value = str(value)
    elif re.match("[0-9.]+", value):
        # normalize float values
        value = str(float(value))
    return value.upper()


@attr.s(frozen=True)
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
        default=Bandwidth._25,
        validator=attr.validators.instance_of(Bandwidth),
        converter=Bandwidth.from_any,
    )
    # configurable squelch for analog
    squelch = attr.ib(
        default=1,
        validator=attr.validators.instance_of(int),
        converter=int,
    )


@attr.s(frozen=True)
class DigitalChannel(Channel):
    # fixed bandwidth for digital
    bandwidth = Bandwidth._125
    squelch = 0
    color_code = attr.ib(default=1)
    grouplist = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(uuid.UUID)),
        converter=lambda gl: gl._id if isinstance(gl, GroupList) else gl,
    )
    talkgroup = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(Talkgroup)),
    )
    # a list of other static talkgroups, which form the basis of an RX/scan list
    # eq is False here because the static talkgroups can change without necessarily
    # changing the identity of the channel itself
    static_talkgroups = attr.ib(
        eq=False,
        factory=list,
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(Talkgroup)
        ),
    )

    def from_talkgroups(self, talkgroups, **kwargs):
        """
        Return a new channel per talkgroup based on this channel's settings.

        Additional kwargs will be applied to the new channel.
        """

        return [
            attr.evolve(
                self,
                name="{} {}".format(
                    tg.name_with_timeslot[: NAME_MAX - 4],
                    (self.code if self.code else self.name)[:3],
                ),
                talkgroup=tg,
                static_talkgroups=[],
                **kwargs,
            )
            for tg in talkgroups
        ]

    def grouplist_name(self, codeplug):
        if self.grouplist:
            return codeplug.lookup(self.grouplist).name

    @property
    def zone_name(self):
        maybe_code = "{} ".format(self.code) if self.code else ""
        name = "{}{}".format(maybe_code, self.name)
        return name
        # shorten names for channel display
        # for old, new in self.name_replacements.items():
        #    name = name.replace(old, new)
        # return name


@attr.s(frozen=True)
class ScanList:
    """
    A ScanList specifies a set of channels that can be sequentially scanned.
    """

    name = attr.ib(eq=False, validator=attr.validators.instance_of(str))
    channels = attr.ib(
        eq=False,
        factory=tuple,
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(Channel),
            iterable_validator=attr.validators.instance_of(tuple),
        ),
        converter=tuple,
    )
    # stable id can track object across name and contents changes
    _id = attr.ib(factory=uuid.uuid4, repr=False)

    @classmethod
    def from_names(cls, name, channel_names, channels):
        sl_channels = []
        channels_by_name = {ch.name: ch for ch in channels}
        channels_by_short_name = {ch.short_name: ch for ch in channels}
        for cn in channel_names:
            channel = channels_by_name.get(cn, channels_by_short_name.get(cn))
            if channel is None:
                logger.debug(
                    "ScanList {!r} references unknown channel {!r}, ignoring".format(
                        name,
                        cn,
                    )
                )
                continue
            sl_channels.append(channel)
        return cls(name=name, channels=sl_channels)

    @classmethod
    def prune_missing_channels(cls, scanlists, channels):
        """
        Return a sequence of new ScanList objects containing only channels in `channels`
        """
        channels = {ch: ch for ch in channels}
        return [
            sl
            for sl in [
                attr.evolve(
                    sl, channels=[channels[ch] for ch in sl.channels if ch in channels]
                )
                for sl in scanlists
            ]
            if sl.channels
        ]

    @property
    def unique_channels(self):
        return tuple(self.channels)


@attr.s(frozen=True)
class Zone:
    """
    A Zone groups channels together by name
    """

    name = attr.ib(eq=False, validator=attr.validators.instance_of(str))
    channels_a = attr.ib(
        factory=tuple,
        validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)),
        converter=tuple,
    )
    channels_b = attr.ib(
        factory=tuple,
        validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)),
        converter=tuple,
    )

    @classmethod
    def prune_missing_channels(cls, zones, channels):
        """
        Return a sequence of new Zone objects containing only channels in `channels`
        """

        channels = {ch: ch for ch in channels}
        return [
            zn
            for zn in [
                attr.evolve(
                    zn,
                    channels_a=tuple(
                        channels[ch] for ch in zn.channels_a if ch in channels
                    ),
                    channels_b=tuple(
                        channels[ch] for ch in zn.channels_b if ch in channels
                    ),
                )
                for zn in zones
            ]
            if zn.channels_a + zn.channels_b
        ]

    @property
    def unique_channels(self):
        channels = list(self.channels_a)
        for ch in self.channels_b:
            if ch not in channels:
                channels.append(ch)
        return tuple(channels)


@attr.s
class Ordering:
    contacts = attr.ib(factory=tuple, converter=tuple)
    channels = attr.ib(factory=tuple, converter=tuple)
    grouplists = attr.ib(factory=tuple, converter=tuple)
    scanlists = attr.ib(factory=tuple, converter=tuple)
    zones = attr.ib(factory=tuple, converter=tuple)

    object_names = ("contacts", "channels", "grouplists", "scanlists", "zones")

    @classmethod
    def from_csv(cls, ordering_csv):
        order = {}
        csvr = csv.DictReader(ordering_csv)
        for r in csvr:
            for obj, item in r.items():
                if not item:
                    continue
                if obj.lower() not in cls.object_names:
                    raise KeyError("{!r} not in {!r}".format(obj, cls.object_names))
                order.setdefault(obj.lower(), []).append(item)
        return cls(**order)

    def __add__(self, other):
        if not isinstance(other, type(self)):
            return None
        return type(self)(
            **{
                attribute.name: getattr(self, attribute.name)
                + getattr(other, attribute.name)
                for attribute in attr.fields(type(self))
            }
        )

    def __bool__(self):
        return any(attr.asdict(self, recurse=False).values())


@attr.s
class Replacements(Ordering):
    @classmethod
    def from_csv(cls, replacements_csv):
        csvr = csv.DictReader(replacements_csv)
        f_r_map = {"pattern": {}, "repl": {}}
        for r in csvr:
            for header, item in r.items():
                if not item:
                    continue
                obj, _, f_r = header.partition("_")
                obj_l = obj.lower()
                if obj_l not in cls.object_names:
                    raise KeyError("{!r} not in {!r}".format(obj, cls.object_names))
                try:
                    f_r_map[f_r.lower()].setdefault(obj_l, []).append(item)
                except KeyError as ke:
                    raise KeyError(
                        "Expecting one of {!r}, not {}".format(
                            tuple(f"{obj_l}_{k}" for k in f_r_map),
                            header,
                        ),
                    ) from ke
        f_r_tuples = {}
        for obj, find_pats in f_r_map["pattern"].items():
            f_r_tuples[obj] = tuple(zip(find_pats, f_r_map["repl"][obj]))
        return cls(**f_r_tuples)


class DuplicateDmrID(Warning):
    """2 contacts with different names have the same ID."""


def uniquify_contacts(contacts, ignore_timeslot=False):
    """
    Return a sequence of contacts with all duplicates removed.

    If any duplicate names are found without matching numbers, an exception is raised.

    If any two names point to the same number, a warning is emitted.

    :param key: function determines the deduplication key, default: (name, timeslot)
    """
    ctd = {}
    for ct in contacts:
        if ignore_timeslot:
            ct_key = ct.name
        else:
            ct_key = (ct.name, ct.timeslot) if isinstance(ct, Talkgroup) else ct.name
        stored_ct = ctd.setdefault(ct_key, ct)
        if stored_ct.dmrid != ct.dmrid:
            raise RuntimeError(
                "Two contacts named {} have different IDs: {} {}. "
                "Rename one of the contacts.".format(ct.name, ct.dmrid, stored_ct.dmrid)
            )
    # check for duplicate DMR numbers, drop and warn
    contacts_by_id = {}
    for ct in ctd.values():
        if ignore_timeslot:
            ct_key = (ct.dmrid, ct.kind)
        else:
            ct_key = (
                (ct.dmrid, ct.kind, ct.timeslot)
                if isinstance(ct, Talkgroup)
                else (ct.dmrid, ct.kind)
            )
        stored_ct = contacts_by_id.setdefault(ct_key, ct)
        if stored_ct.name != ct.name:
            warnings.warn(
                "Two contacts with different names ({!r}, {!r}) "
                "have the same ID: {}. Using {!r}.".format(
                    stored_ct.name, ct.name, stored_ct.dmrid, stored_ct.name
                ),
                DuplicateDmrID,
            )
    return tuple(contacts_by_id.values())


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
    _lookup_table = attr.ib(default=None, init=False, eq=False, repr=False)

    def _generate_lookup_table(self):
        """
        Build a UUID -> object dict for quick lookups when building the codeplug.

        Not an attrs attribute, because new instances should NOT inherit
        the previous instances lookup table, and we don't necessarily
        want to build the table until it's going to be used.
        """
        lookup_table = {}
        for obj_list in [self.grouplists, self.scanlists]:
            for obj in obj_list:
                assert obj._id not in obj_list, "UUID Key collision: {}".format(obj.id)
                lookup_table[obj._id] = obj
        return lookup_table

    def lookup(self, object_id):
        """
        Lookup a codeplug object by ID
        """
        if self._lookup_table is None:
            self._lookup_table = self._generate_lookup_table()
        return self._lookup_table[object_id]

    def filter(
        self,
        include=None,
        exclude=None,
        order=None,
        reverse_order=None,
        ranges=None,
        replacements=None,
    ):
        """
        Filter codeplug objects and return a new Codeplug.

        :param include: Ordering object of codeplug objects to retain
        :param exclude: Ordering object of codeplug objects to return
        :param order: Ordering object specifying top down order
        :param reverse_order: Ordering object specifying bottom up order
        :param ranges: Frequency ranges of channels to retain
        :param replacements: Replacements of regex subs to make in channel names
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

        # regex find and replace
        def _replace_filter(objects, ordering_list):
            pats = tuple((re.compile(p), r) for p, r in ordering_list)

            def _replace_name(object):
                new_name = object.name
                for pat, repl in pats:
                    new_name = pat.sub(repl, new_name)
                if new_name != object.name:
                    return attr.evolve(object, name=new_name)
                return object

            return [_replace_name(o) for o in objects]

        # order static_talkgroups based on contact order
        def order_static_talkgroups(ch):
            return attr.evolve(
                ch,
                static_talkgroups=[
                    tg for tg in cp["contacts"] if tg in ch.static_talkgroups
                ],
            )

        def update_talkgroup(ch):
            try:
                updated_talkgroup = cp["contacts"][cp["contacts"].index(ch.talkgroup)]
                if ch.talkgroup.name != updated_talkgroup.name:
                    return attr.evolve(
                        ch,
                        talkgroup=updated_talkgroup,
                    )
            except ValueError:
                pass
            return ch

        def update_talkgroup_refs(ch):
            if isinstance(ch, DigitalChannel):
                if ch.static_talkgroups:
                    return order_static_talkgroups(ch)
                elif ch.talkgroup:
                    # update talkgroup reference to get the latest name
                    return update_talkgroup(ch)
            return ch

        def talkgroup_exists(ch, contact_set):
            if isinstance(ch, AnalogChannel):
                return True
            if ch.static_talkgroups:
                # missing talkgroups will be pruned by `order_static_talkgroups`
                return any(tg in contact_set for tg in ch.static_talkgroups)
            elif ch.talkgroup is not None:
                return ch.talkgroup in contact_set
            else:
                # No talkgroup or static_talkgroups, prune channel
                return False

        if exclude:
            _filter_inplace(exclude, _exclude_filter)
        if order:
            _filter_inplace(order, _order_filter)
        if reverse_order:
            _filter_inplace(
                reverse_order, functools.partial(_order_filter, reverse=True)
            )
        if replacements:
            _filter_inplace(replacements, _replace_filter)
            # Perform exclude, order, reverse_order after making replacements
            # so callers can provider either the original name or replaced name
            # in the in Ordering CSV file
            if exclude:
                _filter_inplace(exclude, _exclude_filter)
            if order:
                _filter_inplace(order, _order_filter)
            if reverse_order:
                _filter_inplace(
                    reverse_order, functools.partial(_order_filter, reverse=True)
                )
        # Check the include list last; must use the final "replaced" name
        # if replacements are used
        if include:
            _filter_inplace(include, _include_filter)

        # Reorder static talkgroups and remove channels with missing talkgroups
        contact_set = set(tg for tg in cp["contacts"])
        cp["channels"] = [
            update_talkgroup_refs(ch)
            for ch in cp["channels"]
            if talkgroup_exists(ch, contact_set)
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
        if not scanlist_dicts:
            return self
        scanlists = {sl.name: sl for sl in self.scanlists}
        for sl_name, channels in scanlist_dicts.items():
            scanlists[sl_name] = ScanList.from_names(
                name=sl_name,
                channel_names=channels,
                channels=self.channels,
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
        zone_names = set(z.name for z in zones)
        channels = []
        exp_scanlists = []
        for ch in self.channels:
            if not isinstance(ch, DigitalChannel) or not ch.static_talkgroups:
                channels.append(ch)
                continue
            exp_zone_name = unique_name(ch.short_name, zone_names)
            zscanlist = ScanList(
                name=exp_zone_name,
                channels=[],
            )
            zone_channels = ch.from_talkgroups(
                ch.static_talkgroups,
                scanlist=zscanlist,
            )
            exp_scanlists.append(attr.evolve(zscanlist, channels=zone_channels))
            zones.append(
                Zone(
                    name=exp_zone_name,
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
