"""
dzcb.model - data model for codeplug objects
"""
import csv
import enum
import json
from importlib_resources import files
import logging
import re

import attr
import requests

# cached data for testing
import dzcb.data
import dzcb.munge

# XXX: i hate this
NAME_MAX = 16


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

    name = attr.ib(eq=True)
    dmrid = attr.ib(eq=True, order=True, converter=int)
    kind = attr.ib(
        eq=True,
        default=ContactType.GROUP,
        validator=attr.validators.instance_of(ContactType),
        converter=ContactType.from_any,
    )


@attr.s(eq=True, frozen=True)
class Talkgroup(Contact):
    timeslot = attr.ib(
        eq=True,
        order=True,
        default=Timeslot.ONE,
        validator=attr.validators.instance_of(Timeslot),
        converter=Timeslot.from_any,
    )

    all_talkgroups_by_id = {}

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
        return cls(**fields)


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
    )
    power = attr.ib(
        default=Power.HIGH,
        validator=attr.validators.instance_of(Power),
        converter=Power.from_any,
    )
    rx_only = attr.ib(
        default=False,
        validator=attr.validators.instance_of(bool)
    )
    scanlist = attr.ib(default=None)
    code = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))

    def __attrs_post_init__(self):
        type(self)._all_channels[self.name] = self

    @property
    def short_name(self):
        """Generate a unique short name for this channel"""
        attempt = 0
        maybe_this_channel = None
        while maybe_this_channel != self:
            maybe_short_name = dzcb.munge.channel_name(
                self.name,
                NAME_MAX - (1 if attempt else 0)
            ) + (str(attempt) if attempt else "")
            maybe_this_channel = type(self)._short_names.setdefault(maybe_short_name, self)
            attempt += 1
            if attempt > 9:
                raise RuntimeError("Cannot find a non-conflicting channel short name for {}".format(self))
        return maybe_short_name


@attr.s
class AnalogChannel(Channel):
    tone_encode = attr.ib(default=None)
    tone_decode = attr.ib(default=None)
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
    talkgroup = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(Talkgroup)))
    # a list of other static talkgroups, which form the basis of an RX/scan list
    static_talkgroups = attr.ib(factory=list)

    def from_talkgroups(self, talkgroups, order=None):
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
                static_talkgroups=[]
            ) for tg in dzcb.munge.ordered(talkgroups, order or [], key=lambda tg: tg.name)
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


@attr.s
class ScanList:
    """
    A ScanList specifies a set of channels that can be sequentially scanned.
    """
    name = attr.ib(validator=attr.validators.instance_of(str))
    channels = attr.ib(factory=list, validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)))

    @classmethod
    def from_names(cls, name, channel_names):
        channels = []
        for cn in channel_names:
            channel = Channel._short_names.get(cn, Channel._all_channels.get(cn))
            if channel is None:
                print(
                    "ScanList {!r} references unknown channel {!r}, ignoring".format(
                        name, cn,
                    )
                )
                continue
            channels.append(channel)
        return cls(
            name=name,
            channels=channels
        )

    @classmethod
    def prune_missing_channels(cls, scanlists, channels):
        """
        Return a sequence of new ScanList objects containing only channels in `channels`
        """
        return [
            attr.evolve(
                sl,
                channels=[ch for ch in sl.channels if ch in channels]
            )
            for sl in scanlists
        ]

    @property
    def unique_channels(self):
        return list(self.channels)


@attr.s
class Zone:
    """
    A Zone groups channels together by name
    """
    name = attr.ib(validator=attr.validators.instance_of(str))
    channels_a = attr.ib(factory=list, validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)))
    channels_b = attr.ib(factory=list, validator=attr.validators.deep_iterable(attr.validators.instance_of(Channel)))

    @property
    def unique_channels(self):
        channels = list(self.channels_a)
        for ch in self.channels_b:
            if ch not in channels:
                channels.append(ch)
        return channels


def uniquify_contacts(contacts):
    """
    Return a sequence of contacts with all duplicates removed.

    If any duplicate names are found without matching numbers, an exception is raised.
    """
    ctd = {}
    for ct in contacts:
        stored_ct = ctd.setdefault(ct.name, ct)
        if stored_ct.dmrid != ct.dmrid:
            raise RuntimeError("Two contacts named {} have different IDs: {} {}".format(ct.name, ct.dmrid, stored_ct.dmrid))
    return list(ctd.values())


@attr.s
class Codeplug:
    contacts = attr.ib(factory=list, converter=uniquify_contacts)
    channels = attr.ib(factory=list)
    grouplists = attr.ib(factory=list)
    scanlists = attr.ib(factory=list)
    zones = attr.ib(factory=list)

    def __attrs_post_init__(self):
        # prune any channels which are not in a zone
        all_channels = []
        for z in self.zones:
            all_channels.extend(z.unique_channels)
        self.channels = [ch for ch in self.channels if ch in all_channels]

    def order_zones(self, zone_order=None, exclude_zones=None):
        if zone_order is None:
            zone_order = []
        if exclude_zones is None:
            exclude_zones = []

        zones = [
            zone
            for zone in dzcb.munge.ordered(self.zones, zone_order, key=lambda z: z.name)
            if zone.name not in exclude_zones
        ]
        return type(self)(
            contacts=list(self.contacts),
            channels=list(self.channels),
            grouplists=list(self.grouplists),
            scanlists=list(self.scanlists),
            zones=zones,
        )

    def order_grouplists(self, static_talkgroup_order=None, exclude_talkgroups=None):
        """
        Reorder the Talkgroups within each grouplist according to static_talkgroup_order.

        Exclude any talkgroups by name in exclude_talkgroups
        """
        if static_talkgroup_order is None:
            static_talkgroup_order = []
        if exclude_talkgroups is None:
            exclude_talkgroups = []

        grouplists = [
            attr.evolve(
                gl,
                contacts=dzcb.munge.ordered(
                    seq=[c for c in gl.contacts if c not in exclude_talkgroups],
                    order=static_talkgroup_order,
                )
            )
            for gl in self.grouplists
        ]
        return type(self)(
            contacts=list(self.contacts),
            channels=list(self.channels),
            grouplists=grouplists,
            scanlists=list(self.scanlists),
            zones=list(self.zones),
        )

    def filter_frequency_range(self, *ranges):
        """
        :param ranges: tuple of (low, high) frequency to keep in the codeplug
        """
        def freq_in_range(freq):
            for low, high in ranges:
                if float(low) < freq < float(high):
                    return True
            return False

        channels = []
        channels_pruned = []

        for ch in self.channels:
            if freq_in_range(ch.frequency):
                channels.append(ch)
                continue
            # none of the ranges matched, so prune this channel
            channels_pruned.append(ch)
        if channels_pruned:
            print("Excluding {} channels with frequency out of range: {}".format(len(channels_pruned), ranges))

        # prune channels from scanlists
        scanlists = []
        for scanlist in self.scanlists:
            sc_channels = [ch for ch in scanlist.channels if ch not in channels_pruned]
            if sc_channels:
                scanlists.append(ScanList(name=scanlist.name, channels=sc_channels))

        # prune channels from zones
        zones = []
        for zone in self.zones:
            zn_channels_a = [ch for ch in zone.channels_a if ch not in channels_pruned]
            zn_channels_b = [ch for ch in zone.channels_b if ch not in channels_pruned]
            if zn_channels_a or zn_channels_b:
                zones.append(Zone(name=zone.name, channels_a=zn_channels_a, channels_b=zn_channels_b))

        return type(self)(
            contacts=list(self.contacts),
            channels=channels,
            grouplists=list(self.grouplists),
            scanlists=ScanList.prune_missing_channels(self.scanlists, channels),
            zones=zones,
        )

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
            zone_channels = ch.from_talkgroups(ch.static_talkgroups, order=static_talkgroup_order)
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

        return type(self)(
            contacts=list(self.contacts),
            channels=channels,
            grouplists=list(self.grouplists),
            # Don't reference channels that no longer exist
            scanlists=ScanList.prune_missing_channels(self.scanlists, channels) + exp_scanlists,
            zones=zones,
        )
