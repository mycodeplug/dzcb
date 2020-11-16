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
from bs4 import BeautifulSoup
import requests

# cached data for testing
import dzcb.data

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
    dmrid = attr.ib(eq=True, order=True)
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


@attr.s
class Channel:
    """Common channel attributes"""

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
        default=2,
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
                static_talkgroups=[]
            ) for tg in talkgroups
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
    channels = attr.ib(factory=list)


@attr.s
class Zone:
    """
    A Zone groups channels together by name
    """
    name = attr.ib(validator=attr.validators.instance_of(str))
    channels_a = attr.ib(factory=list)
    channels_b = attr.ib(factory=list)

    @property
    def unique_channels(self):
        channels = list(self.channels_a)
        for ch in self.channels_b:
            if ch not in channels:
                channels.append(ch)
        return channels


@attr.s
class Codeplug:
    contacts = attr.ib(factory=list)
    channels = attr.ib(factory=list)
    grouplists = attr.ib(factory=list)
    scanlists = attr.ib(factory=list)
    zones = attr.ib(factory=list)

    def expand_static_talkgroups(self):
        """
        :return: new Codeplug with additional channels and zones for each
            DigitalChannel with static_talkgroups
        """
        zones = list(self.zones)
        channels = list(self.channels)
        scanlists = list(self.scanlists)
        for ch in self.channels:
            if not isinstance(ch, DigitalChannel):
                continue
            if not ch.static_talkgroups:
                continue
            zone_channels = ch.from_talkgroups(ch.static_talkgroups)
            channel_names = [zc.name for zc in zone_channels]
            zscanlist = ScanList(
                name=ch.name,
                channels=channel_names,
            )
            scanlists.append(zscanlist)
            for zch in zone_channels:
                if zch.scanlist is None:
                    zch.scanlist = zscanlist
            zones.append(
                Zone(
                    name=ch.name,
                    channels_a=channel_names,
                    channels_b=channel_names,
                )
            )
            channels.extend(zone_channels)
        return type(self)(
            contacts=list(self.contacts),
            channels=channels,
            grouplists=list(self.grouplists),
            scanlists=scanlists,
            zones=zones,
        )
