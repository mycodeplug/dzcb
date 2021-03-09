#!/usr/bin/env bash

# This script generates the same codeplug as generate.py
# by running dzcb as a command line program

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OUTPUT=${OUTPUT:-$DIR/../../OUTPUT}
python -m dzcb \
    --pnwdigital \
    --seattledmr \
    --default-k7abd \
    --farnsworth-template-json $DIR/md380-uhf.json \
                               $DIR/md380-vhf.json \
                               $DIR/md390-uhf.json \
                               $DIR/md390-vhf.json \
    --scanlists-json $DIR/scanlists.json \
    --exclude $DIR/exclude.csv \
-- $OUTPUT/$(dirname "$DIR")
