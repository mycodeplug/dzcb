# dzcb

DMR Zone Channel Builder for TYT MD-UV380 and similar.

Data is sourced from PNWDigital.net and cached in this repo.

# Usage

    python -m dzcb /path/to/output

Given the inputs:

* Digital Repeaters
    * Talkgroups present on each repeater
* Digital Channels
* Analog Channels
* Contacts (talkgroups)

Generate the outputs:

* Channel List
* Zones for each repeater, channel
    * RX lists for each timeslot in each zone

# Customization

The code plug may be customized by supplying a json file with various
parameters as described below:

```
{
    "exclude_zones": [],
    "zone_order": [],
    "zone_name_format": "",
    "talkgroup_order": [],
    "talkgroup_name_format": "",
    "a_ts1_first": true,
    "b_ts2_first": true,
    "channel_name_format": "",
    "rx_same_timeslot": true
}
```

## `exclude_zones`

Do not generate zone or channels for the listed repeaters.

## `zone_order`

Specify the preferred ordering of zones. Any zones not mentioned in this list
will be appended in alphabetic order.

Zones can be given by any unique identifier, but typically short code is
preferred.

## `zone_name_format`

Default: `"{code} {city} {name}"`

## `talkgroup_order`

Specify preferred ordering of talkgroup channels within a zone. Specify by name
or number. Any talkgroups present in the zone not mentioned in this list will
be appended in alphabetic order.

## `talkgroup_name_format`

The format of the displayed talkgroup name.

Default: `"{name} {timeslot} - {dmr_id}"`

## `a_ts1_first`

If true, the zone's "A" bank will list all timeslot 1 talkgroups before any
timeslot 2 talkgroups. Otherwise, use `talkgroup_order`.

## `b_ts2_first`

If true, the zone's "B" bank will list all timeslot 2 talkgroups before any
timeslot 1 talkgroups. Otherwise, use `talkgroup_order`.

## `channel_name_format`

The format of the displayed chanel name.

Default: `"{talkgroup} {code}"`

## `rx_same_timeslot`

If true, the channel will receive all talkgroups on the frequency using the
same timeslot. It can be useful to monitor other communications on the timeslot
before keying up an unrelated talkgroup.
