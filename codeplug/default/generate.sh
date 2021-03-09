#!/usr/bin/env bash

# This script generates the same codeplug as generate.py
# by running dzcb as a command line program

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OUTPUT=${OUTPUT:-$DIR/../../OUTPUT}
python -m dzcb \
    --pnwdigital \
    --seattledmr \
    --default-k7abd \
    --repeaterbook-state washington oregon \
    --repeaterbook-name-format '{Nearest City} {Frequency}' \
    --repeaterbook-proximity-csv "$DIR/../../src/dzcb/data/repeaterbook_proximity_zones.csv" \
    --scanlists-json $DIR/scanlists.json \
    --replacements $DIR/replacements.csv \
    --order $DIR/order.csv \
    --anytone \
    --dmrconfig-template \
    --farnsworth-template-json \
    --gb3gf \
-- $OUTPUT/$(dirname "$DIR")
