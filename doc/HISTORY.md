# `dzcb` History

`dzcb` is written by Masen Furer KF7HVM <kf7hvm@0x26.net>.

## Motivation

`dzcb` development began in late October 2020 in response to the lack of
existing tools for creating a TYT MD-UV380 codeplug from a matrix of repeater
frequencies and talkgroups.

The [PNWDigital](http://pnwdigital.net) group publishes information on its
repeater system in standard format CSV files (K7ABD format) which are generated
directly from the network cBridges, and I wanted to use these files to directly
generate a cross-platform compatible codeplug targeting the TYT MD-UV380, using
[editcp](https://www.farnsworth.org/dale/codeplug/editcp/).

And thus `dzcb` was born.

## Criticism

> Why did you need to write 3800 lines of code over 6 months to do what I could
> do with an afternoon and a spreadsheet program?

Well, I _personally_ don't like editing codeplugs by hand, neither in a CPS or
in a spreadsheet.

The CPS experience is hit or miss depending on what radio you have and
any work done in a CPS to edit a codeplug will generally not be applicable
to other radio types. Vendor CPS packages are "different enough" from each
other, often buggy, and only support Windows.

The spreadsheet experience can be slightly better (at least you're using find/replace
instead of clicking through lists and buggy forms). However, the problem
with most CSV import formats is _they key on object name_, so renaming objects
can be problematic, and needs to occur in multiple places (and possibly,
multiple separate files).

Finally, neither CPS nor CSV solve the problem of expanding a list of talkgroups
across a single repeater, and the existing tools only support Anytone CPS format.

_(Please email kf7hvm@0x26.net with further criticism and I will respond publicly here)_


## Feature Development

### Repeaterbook

Since [repeaterbook](http://repeaterbook.com) is the primary source of analog
repeater information in the region, I added support for automatically
downloading up-to-date repeater records and formatting those in the same K7ABD
analog format.

Rather than download and assemble the zone/channel CSV by hand (copy/paste from
RB), it made more sense to define a new CSV file with points of interest,
distances, and desired bands to create the channels entries fresh whenever the
codeplug is built.

When repeater information is incorrect in the codeplug, it can be updated on
Repeaterbook to benefit everyone.

### More Output Formats

Along the way, additional output formats were added based on recommendation
or needs.

#### GB3GF OpenGD77

This format is the only good way to represent an OpenGD77 codeplug in CSV format
and is a defacto standard in the opengd77 world.

Because the opengd77 firmware handles static talkgroups much differently than
other common radios, it required a significant restructuring of the internal
representation of the codeplug. Ultimately this architectural change made it
easier to represent a single channel with multiple talkgroups which could later
be expanded into multiple channels.

#### Anytone CSV

Anytone radios are popular and many people prefer to use the official CPS despite
the fact that it only runs on windows. Support for Anytone CPS import format was
added to achieve parity with existing codeplug generators. The implementation is
flexible such that future CPS format changes can be easily accomodated.

#### dmrconfig

On the advice of Dave W7NCX, support for the cross platform cli tool
[`dmrconfig`](https://github.com/OpenRTX/dmrconfig) textual codeplug
format was added.

### Advanced Filtering

In response to user feedback, a new CSV format was created to allow an end user
to customize names, include/exclude objects, and reorder zones, contacts, and
channels within a codeplug.

These modifications are performed against the original source files so there is
no "manual" effort when the upstream data source updates the talkgroup deck,
color code or frequency. The name and ordering will be applied to the updated
channels as before.

### `example-codeplug`

An [example codeplug](https://github.com/mycodeplug/example-codeplug) and
additional documentation was added to facilitate use by others in the
community.
