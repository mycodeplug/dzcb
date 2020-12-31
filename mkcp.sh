#!/usr/bin/env bash

. ~/code/VENV/dzcb/bin/activate
mkdir -p /tmp/cpdata
cp ~/code/dzcb/codeplug/k7abd/* /tmp/cpdata
python -m dzcb.pnwdigital /tmp/cpdata
python -m dzcb.seattledmr /tmp/cpdata
export REPEATERBOOK_USER=kf7hvm
python -m dzcb.repeaterbook \
        ~/code/dzcb/codeplug/repeaterbook_proximity_zones.csv \
        /tmp/cpdata

python -m dzcb \
	--farnsworth-template ~/codeplug/2020-12-11_farnsworth_template.json \
	/tmp/cpdata ~/codeplug/dzcb/$(date \+%Y-%m-%d)
