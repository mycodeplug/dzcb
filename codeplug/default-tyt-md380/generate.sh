#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OUTPUT=${OUTPUT:-$DIR/../../OUTPUT}
python -m dzcb \
    --pnwdigital \
    --seattledmr \
    --default-k7abd \
    --scanlists-json $DIR/scanlists.json \
    --order-json $DIR/order.json \
    --farnsworth-template-json $DIR/md380-uhf.json \
    --farnsworth-template-json $DIR/md380-vhf.json \
    --farnsworth-template-json $DIR/md390-uhf.json \
    --farnsworth-template-json $DIR/md390-vhf.json \
$OUTPUT/default-tyt-md380
