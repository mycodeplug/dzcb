# dzcb

**D**MR **Z**one **C**hannel **B**uilder

* Fetch - fetch input files from local directories or urls
* Assemble - combine information from multiple sources
* Filter - rename, exclude, reorder zones, and talkgroups
* Format - output to common export formats

## [Overview Video](https://youtu.be/RfokJM5rpsM)

<img src="/doc/dzcb-overview.svg">

## See [Releases](https://github.com/mycodeplug/dzcb/releases) for Default Codeplugs

## Github Actions

For more information on generating customized codeplugs in the cloud without
installing any software, see **[WALKTHROUGH](./doc/WALKTHROUGH.md)**.

The walkthrough uses
[mycodeplug/example-codeplug](https://github.com/mycodeplug/example-codeplug)
[[input files](https://github.com/mycodeplug/example-codeplug/tree/main/input/default)]

# Output Formats

## Farnsworth JSON

For import into [editcp](https://www.farnsworth.org/dale/codeplug/editcp/),
with theoretical support for:

* TYT
  * MD-380, MD-390
  * MD-UV380 (tested), MD-UV390
  * MD-2017 
* Alinco DJ-MD40 
* Retevis RT3, RT3-G, RT3S, and RT82 radios

Use `--farnsworth-template-json` to specify an exported codeplug to
use as the template for settings and radio capabilities.

`dzcb` includes basic template files for [MD380/390](./codeplug/default-tyt-md380)
and [MD-UV380/390](./src/dzcb/data/farnsworth).

Generated JSON files will be written to the `editcp` subdir of the output directory.

## [OpenRTX/dmrconfig](https://github.com/OpenRTX/dmrconfig)

For import into [`dmrconfig`](https://github.com/OpenRTX/dmrconfig) 1.1
utility with theoretical support for:

* Anytone AT-D868UV
* Anytone AT-D878UV
* BTECH DMR-6x2
* Baofeng DM-1801
* Radioddity GD-77
* TYT MD-380
* TYT MD-390
* Zastone D900
* Zastone DP880
* Radtel RT-27D
* Baofeng RD-5R
* TYT MD-UV380
* TYT MD-UV390
* TYT MD-2017
* TYT MD-9600
* Retevis RT84

Use `--dmrconfig-template` to specify an exported codeplug config to use as a
template for radio type, messages, DMR ID,  and startup text. The `dmrconfig` subdir
of the output directory will contain a dmrconfig config per template specified.

## Anytone CPS

For import into the official Anytone CPS (windows-only).

`dzcb` generates Channels.CSV, Talkgroups.CSV, ScanList.CSV, and Zone.CSV in the `anytone` subdir
of the output directory.

### Versions Supported

* **AT-D578UV** [CPS 1.11](https://cdn.shopify.com/s/files/1/0833/9095/files/D578UV_V1.11_official_release_200918.zip)
  * [Bridgecom Support](https://bridgecomsystems.freshdesk.com/support/solutions/articles/63000106309-anytone-578-cps-and-firmware-downloads)
* **AT-D868UV** [CPS 1.39](https://cdn.shopify.com/s/files/1/0833/9095/files/D868UV_2.39_official_200807.zip)
  * [Bridgecom Support](https://bridgecomsystems.freshdesk.com/support/solutions/articles/63000105671-anytone-868-cps-firmware-and-driver-versions)
* **AT-D878UV** [CPS 1.21](https://cdn.shopify.com/s/files/1/0833/9095/files/D878UV_V1.21_official_release_200918.zip)  
  * [Bridgecom Support](https://bridgecomsystems.freshdesk.com/support/solutions/articles/63000105978-anytone-878-878-plus-cps-firmware-and-driver-downloads)

(links fetched 2021/01/24)

## GB3GF OpenGD77 CSV

For import into [GB3GF CSV tool](http://www.gb3gf.co.uk/downloads.html).
Currently only supporting OpenGD77 target. Tool is "windows-only" but
runs decently under wine.

If `--gb3gf` is specified, the `gb3gf/opengd77` subdir of the output directory will
contain the 4 CSV files used by the program:

  * `Channels.csv`
  * `Contacts.csv`
  * `TG_Lists.csv`
  * `Zones.csv`
  
Note: these files are actually semicolon separated.

# Input Format

## K7ABD style

A directory of inter-related CSV files describing the common settings
needed to program all radios. This is a common format used by K7ABD's
original [anytone-config-builder](https://www.k7abd.net/anytone-config-builder/)
and N7EKB's [cps-import-builder](https://github.com/n7ekb/cps-import-builder).

An arbitrary number of files and folders will be combined. At this time duplicate
zone names in different files may be problematic. Keep zone names unique.
Particularly be wary of trucated names.

* `Analog__ZoneName.csv`
  * Zone, Channel Name, Bandwidth, Power, RX Freq, TX Freq, CTCSS Decode, CTCSS Encode, TX Prohibit
* `Talkgroups__ZoneName.csv`
  * **No Header Row** tuples of: talkgroup_name,talkgroup_number
  * To specify a **Private** call, suffix the talkgroup number with a "P"
* `Digital-Other__ZoneName.csv` -- only really useful for digital simplex channels or private call
  * Zone, Channel Name, Power, RX Freq, TX Freq, Color Code, Talk Group, TimeSlot, Call Type, TX Permit
* `Digital-Repeaters__ZoneName.csv` -- each line is a digital channel with static talkgroup timeslot assignments
  * Zone Name, Comment, Power, RX Freq, TX Freq, Color Code, talkgroup1, talkgroup2, talkgroup3, ...
  * Typically the Zone Name field is semicolon separated: "Longer Name;LNM"
  * The value for the talkgroup column should be "-", "1", or "2"
  * The talkgroup names must exist in the talkgroups file.
  * Some codeplug targets will create a zone for each frequency with channels for each static talkgroup.
  
## Data Sources

### [PNWdigital.net](http://PNWDigital.net)

**Before using this network, please read the [quick start](http://www.pnwdigital.net/quick-start.html)**

When building a codeplug with the `--pnwdigital` switch, 
data is downloaded from [PNWDigital.net/files/acb](http://www.pnwdigital.net/files/acb/).
The files are updated regularly from the cBridge, so there
could be test data or repeaters that are not yet active.

The data is cached by [`dzcb.pnwdigital`](./src/dzcb/pnwdigital.py)

### [SeattleDMR](https://seattledmr.org/)

**Before using these repeaters, please read the website**

When building a codeplug with the `--seattledmr` switch,
data is downloaded from [seattledmr.org/ConfigBuilder/Digital-Repeaters-Seattle-addon.csv](https://seattledmr.org/ConfigBuilder/Digital-Repeaters-Seattle-addon.csv)
and cleaned up a bit in [`dzcb.seattledmr`](./src/dzcb/seattledmr.py)

### Repeaterbook Proximity

Download live analog Repeaterbook data within distance of point of
interest.

`--repeaterbook-proximity-csv` references a csv file with the fields:

* Zone Name,Lat,Long,Distance,Unit,Band(2m;1.25m;70cm),Use,Operational Status,etc

See example: [`src/dzcb/data/repeaterbook_proximity_zones.csv`](/src/dzcb/data/repeaterbook_proximity_zones.csv)

The fields after Band are optional and correspond directly to the field names
and values in the [Repeaterbook API](https://www.repeaterbook.com/wiki/doku.php?id=api)
(see examples).

`--repeaterbook-state` is a space-separated list of US states or Canadian
provinces that should be included in the proximity search. Including more
states will increase the time required to generate the codeplug.

Repeaterbook API data is downloaded and cached in a user and platform-specific
cache directory. Data will be refreshed if it is older than 12 hours. When
downloading from Repeaterbook, a delay of 30 seconds is introduced between
requests to reduce load on the repeaterbook servers.

Please respect their servers and submit changes requests to repeaterbook
directly.

See [`dzcb.repeaterbook`](./src/dzcb/repeaterbook.py).

#### Example Format

```
Zone Name,Lat,Long,Distance,Unit,Band(2m;1.25m;70cm),Use,Operational Status
Longview WA 35mi,46.13819885,-122.93800354,35,miles,2m;70cm,OPEN,On-air
Longview WA VHF 35mi,46.13819885,-122.93800354,35,miles,2m,open,On-air
Longview WA UHF 35mi,46.13819885,-122.93800354,35,miles,70cm,OPEN,On-Air
```

(it's easy to search on repeaterbook and copy the info from the URL!)

### Simplex, GMRS, etc

Some common [Digital](./src/dzcb/data/k7abd/Digital-Others__Simplex.csv)
and [Analog](./src/dzcb/data/k7abd/Analog__Simplex.csv) simplex frequencies,
and [GMRS/FRS and MURS channels](./src/dzcb/data/k7abd/Analog__Unlicensed.csv) are
included if `--default-k7abd` is specified.

# Customization

The channels, zones, and contacts present and the ordering of such in the
final generated codeplug is controlled by one or more CSV files passed
as parameters.

The column headers correspond to the codeplug objects (zones, contacts, channels,
etc) and may appear in any order or be omitted (if no change is requested to
that type of codeplug object).

The names used in include, exclude, and order are *python regular expressions*
that match from the beginning of the object name. They are prefix match by
default.  To opt-out of prefix match, add a `$` at the end. All regular
expression special characters should be escaped (`\`).

## `--include`

If the CSV file is passed as a `--include` parameter, then any objects not explicitly
mentioned in the file will be removed.

## `--exclude`

If the CSV file is passed as an `--exclude` parameter, then any objects mentioned
will be removed.

See example: [`codeplug/default-tyt-md380/exclude.csv`](/codeplug/default-tyt-md380/exclude.csv)
(for radios with lower channel/zone capacity)

## `--order`

Alphabetic sorting by filename is used when initially building the zones and channels
from K7ABD input files. No implicit sorting by object name occurs.

Any remaining objects are sorted according to the order specified in the file
passed to `--order`. Similarly, a file may be specified as `--reverse-order` which
will sort in reverse, starting from the end of the list.

See example: [`codeplug/default/order.csv`](/codeplug/default/order.csv)

## `--replacements`

The replacements CSV column headers are like `object_pattern,object_repl` and
correspond exactly to the arguments passed to python's
[`re.sub`](https://docs.python.org/3/library/re.html#re.sub). Similar to the
ordering csv, `object` would refer to zones, contacts, channels, etc.

The replacements will be applied to the name of each object of the given
type in the listed order. Subsequent patterns will affect previous
replacements. Unlike the previous group, these regular expressions are
case sensitive, support capturing groups, and indexed replacement.

See example: [`codeplug/default/replacements.csv`](/codeplug/default/replacements.csv)

## `--repeaterbook-name-format`

Python format string used to generate channel names from repeaterbook.

The format string will be passed the Repeaterbook API response dictionary
for the repeater, so all valid fields are usable in the format string.

The default name format is: `"{Callsign} {Nearest City} {Landmark}"`

# Bonus: Trim the Contact List

Download the usersDB.bin with Farnsworth editcp.

    python -m dzcb.contact_trim \
        < "~/.cache/codeplug/Codeplug Editor/usersDB.bin" \
        > "~/.cache/codeplug/Codeplug Editor/usersDB-trimmed.bin"


# Basic Usage

## Installation

```
pip install dzcb
```

## Example

Download live pnwdigital and seattledmr networks and generate a dmrconfig style
codeplug in `/tmp/my-codeplug` with local simplex zones included.

```
python -m dzcb \
    --pnwdigital \
    --seattledmr \
    --default-k7abd \
    --dmrconfig -- /tmp/my-codeplug
```

# Complex Usage

See **[WALKTHROUGH](./doc/WALKTHROUGH.md)** for a step-by-step guide
to getting started with your own customized codeplug build. (The walkthrough
uses [mycodeplug/example-codeplug](https://github.com/mycodeplug/example-codeplug))

## CLI

```
$ python -m dzcb --help
usage: python -m dzcb [-h] [--pnwdigital] [--seattledmr] [--default-k7abd] [--k7abd [DIR [DIR ...]]]
                   [--repeaterbook-proximity-csv [CSV [CSV ...]]] [--repeaterbook-state [STATE [STATE ...]]]
                   [--repeaterbook-name-format REPEATERBOOK_NAME_FORMAT] [--scanlists-json JSON] [--include [CSV [CSV ...]]]
                   [--exclude [CSV [CSV ...]]] [--order [CSV [CSV ...]]] [--reverse-order [CSV [CSV ...]]]
                   [--replacements [CSV [CSV ...]]] [--anytone [RADIO [RADIO ...]]] [--dmrconfig-template [CONF [CONF ...]]]
                   [--farnsworth-template-json [JSON [JSON ...]]] [--gb3gf [RADIO [RADIO ...]]]
                   outdir

dzcb: DMR Zone Channel Builder

positional arguments:
  outdir                Write codeplug files to this directory

optional arguments:
  -h, --help            show this help message and exit
  --pnwdigital          Fetch the latest pnwdigital K7ABD input files
  --seattledmr          Fetch the latest seattledmr K7ABD input files
  --default-k7abd       Include bundled K7ABD input files (simplex + unlicensed)
  --k7abd [DIR [DIR ...]]
                        Specify one or more local directories containing K7ABD CSV files
  --repeaterbook-proximity-csv [CSV [CSV ...]]
                        Fetch repeaters within X distance of POIs defined in a CSV file
  --repeaterbook-state [STATE [STATE ...]]
                        Download repeaters from the given state(s). Default: 'Washington' 'Oregon'
  --repeaterbook-name-format REPEATERBOOK_NAME_FORMAT
                        Python format string used to generate channel names from repeaterbook. See Repeaterbook API response
                        for usable field names. Default: '{Callsign} {Nearest City} {Landmark}'
  --scanlists-json JSON
                        JSON dict mapping scanlist name to list of channel names.
  --include [CSV [CSV ...]]
                        Specify one or more CSV files with object names to include
  --exclude [CSV [CSV ...]]
                        Specify one or more CSV files with object names to exclude
  --order [CSV [CSV ...]]
                        Specify one or more CSV files with object order by name
  --reverse-order [CSV [CSV ...]]
                        Specify one or more CSV files with object order by name (reverse)
  --replacements [CSV [CSV ...]]
                        Specify one or more CSV files with object name replacements
  --anytone [RADIO [RADIO ...]]
                        Generate Anytone CPS CSV files in the 'anytone' subdir for the given radio and CPS versions. If no
                        RADIO+CPS versions are provided, use default set: (578_1_11 868_1_39 878_1_21)
  --dmrconfig-template [CONF [CONF ...]], --dmrconfig [CONF [CONF ...]]
                        Generate dmrconfig conf files in the 'dmrconfig' subdir based on the given template conf files. If no
                        templates are provided, default templates will be used.
  --farnsworth-template-json [JSON [JSON ...]], --editcp [JSON [JSON ...]]
                        Generate Farnsworth editcp JSON format codeplugs in the 'editcp' subdir based on the given template
                        json files. If no templates are provided, default templates will be used.
  --gb3gf [RADIO [RADIO ...]]
                        Generate GB3GF CSV files in the 'gb3gf' subdir for the given radio types. If no radios are provided,
                        use default: (opengd77)
```

## Python API

`dzcb` exposes a python API that is identical to the command line interface
which can be extended to further customize the generation process without
having to directly patch dzcb.

The documentation should improve as the project matures, but for now, see 
[`generate.py`](https://github.com/mycodeplug/example-codeplug/blob/main/input/default/generate.py)
for a real example and [`dzcb.recipe.CodeplugRecipe`](/src/dzcb/recipe.py#L207-L259)
for the implementation details.
        
# Development Usage

## Installation

pip install -e ./dzcb

## Bugs?

Please submit the entire output directory including log files when submitting [issues](/issue/new).
