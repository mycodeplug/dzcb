# dzcb

DMR Zone Channel Builder for TYT MD-UV380 and similar.

Data is sourced from PNWDigital.net and cached in this repo.

# Usage

## Copy template files to a new directory

    mkdir /tmp/cpdata
    cp ./codeplug/k7abd/* /tmp/cpdata/

## Download data files from appropriate locations

    python -m dzcb.pnwdigital /tmp/cpdata
    python -m dzcb.seattledmr /tmp/cpdata
    export REPEATERBOOK_USER=kf7hvm
    export REPEATERBOOK_PASSWD=foo
    python -m dzcb.repeaterbook \
        ./codeplug/repeaterbook_proximity_zones.csv \
        /tmp/cpdata

## Generate the codeplug input files

    python -m dzcb /tmp/cpdata /tmp/codeplug_output

## Trim the Contact List (optional)

Download the usersDB.bin with Farnsworth editcp.

    python -m dzcb.contact_trim \
        < "~/.cache/codeplug/Codeplug Editor/usersDB.bin" \
        > "~/.cache/codeplug/Codeplug Editor/usersDB-trimmed.bin"

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
