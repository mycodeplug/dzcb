"""
dzcb.repeaterbook - export JSON from Repeaterbook, convert to K7ABD CSV format
"""
import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
import os
import time

import geopy.distance
import requests

from . import appdir, AmateurBands
from dzcb import k7abd

logger = logging.getLogger(__name__)

# ?country=United%20States&state=Washington&state=Oregon&state=Idaho&state=California"
REPEATERBOOK_API = "https://www.repeaterbook.com/api/export.php"
REPEATERBOOK_API_DELAY = 30
REPEATERBOOK_LAST_FETCH = 0

# Limit default state to avoid unnecessary API hits
# Users will want to pass the state on the command line
# TODO: Geocode Lat/Long from the CSV file
REPEATERBOOK_DEFAULT_STATES = ("Washington", "Oregon")
REPEATERBOOK_CACHE_MAX_AGE = 3600 * 12.1  # 12 hours (and some change)
REPEATERBOOK_DEFAULT_NAME_FORMAT = "{Callsign} {Nearest City} {Landmark}"
CSV_ZONE_NAME = "Zone Name"
CSV_LAT = "Lat"
CSV_LONG = "Long"
CSV_DISTANCE = "Distance"
CSV_UNIT = "Unit"
CSV_BAND = "Band(2m;1.25m;70cm)"


def cached_json(url, max_age=REPEATERBOOK_CACHE_MAX_AGE):
    md5urlhash = hashlib.md5(url.encode("utf-8")).hexdigest()
    cachedir = Path(appdir.user_cache_dir)
    filepath = cachedir / "repeaters_{}.json".format(md5urlhash)
    if not filepath.exists() or filepath.stat().st_mtime < time.time() - max_age:
        # cache is expired, need to refetch
        cachedir.mkdir(parents=True, exist_ok=True)
        # don't make requests too often
        global REPEATERBOOK_LAST_FETCH
        global_last_fetched = time.time() - REPEATERBOOK_LAST_FETCH
        if global_last_fetched < REPEATERBOOK_API_DELAY:
            time.sleep(REPEATERBOOK_API_DELAY - global_last_fetched)
        resp = requests.get(url)
        REPEATERBOOK_LAST_FETCH = time.time()
        filepath.write_bytes(resp.content)
    return filepath


def iter_cached_repeaters(states=None, max_age=REPEATERBOOK_CACHE_MAX_AGE):
    if states is None:
        states = REPEATERBOOK_DEFAULT_STATES
    for state in states:
        url = "".join(
            (
                REPEATERBOOK_API,
                "?state={}".format(state),
            )
        )
        cached_json_file = cached_json(url, max_age=max_age)
        with open(cached_json_file, "r") as f:
            rb_api_resp = json.load(f)
            logger.info(
                "Load cached Repeaterbook data for %s: %s records (%s)",
                state,
                len(rb_api_resp["results"]),
                cached_json_file,
            )
        for repeater in rb_api_resp["results"]:
            yield repeater


def proximity_zones(proximity_zones_csv):
    csvr = csv.DictReader(
        proximity_zones_csv,
    )
    for zone in csvr:
        name = zone.pop(CSV_ZONE_NAME)
        slug = (
            name.replace(" ", "-").replace(",", "").replace("/", "-").replace("\\", "-")
        )
        yield (name, slug, zone)


def matches_criteria(repeater, criteria):
    for field, value in criteria.items():
        # XXX: maybe need a regex match here...
        if str(value).lower() != str(repeater.get(field, "")).lower():
            return False
    return True


def filter_repeaters(repeaters, zone):
    zone = zone.copy()
    radius = zone.pop(CSV_DISTANCE)
    dunit = zone.pop(CSV_UNIT)
    if radius:
        radius = float(radius)
        poi_coords = (float(zone.pop(CSV_LAT)), float(zone.pop(CSV_LONG)))
    else:
        distance = 0
    bands = [
        AmateurBands.get_normalized(b)
        for b in zone.pop(CSV_BAND).strip().split(";")
        if b
    ]
    matching = []
    # Find matching repeaters
    for r in repeaters:
        if not r:
            continue
        if radius:
            # repeater must be within radius of poi
            repeater_coords = (r["Lat"], r["Long"])
            try:
                distance = geopy.distance.distance(poi_coords, repeater_coords)
            except ValueError:
                repeater_id = (
                    r.get("State ID", "Unknown state"),
                    r.get("Rptr ID", "Unknown repeater"),
                )
                logger.warning(
                    "Ignore repeater {!r} with bogus coordinates: {!r}".format(
                        repeater_id,
                        repeater_coords,
                    )
                )
                continue
            if getattr(distance, dunit) > radius:
                continue
        if bands:
            # repeater frequency must be in the given bands
            if AmateurBands.get_normalized(r["Frequency"]) not in bands:
                continue

        # remaining fields in the zone list are criteria to satisfy
        if matches_criteria(r, zone):
            matching.append((distance, r))
    return [r for _, r in sorted(matching, key=lambda x: x[0])]


def normalize_tone(tone):
    return tone if tone.upper() not in ("", "CSQ") else k7abd.OFF


def repeater_to_k7abd_row(repeater, zone_name, name_format=None):
    if name_format is None:
        name_format = REPEATERBOOK_DEFAULT_NAME_FORMAT
    return {
        k7abd.ZONE: zone_name,
        k7abd.CHANNEL_NAME: name_format.format(**repeater).strip(),
        k7abd.BANDWIDTH: "25K",
        k7abd.POWER: "High",
        k7abd.RX_FREQ: repeater["Frequency"],
        k7abd.TX_FREQ: repeater["Input Freq"] or repeater["Frequency"],
        k7abd.CTCSS_DECODE: normalize_tone(repeater["TSQ"]),
        k7abd.CTCSS_ENCODE: normalize_tone(repeater["PL"]),
        k7abd.TX_PROHIBIT: k7abd.OFF,
    }


def zones_to_k7abd(input_csv, output_dir, states=None, name_format=None):
    repeaters = list(iter_cached_repeaters(states=states))
    for name, slug, zone in proximity_zones(input_csv):
        out_file = Path(output_dir) / "Analog__{}.csv".format(slug)
        total_channels = 0
        with open(out_file, "w", newline="") as out:
            csvw = csv.DictWriter(
                out,
                fieldnames=k7abd.ANALOG_CSV_FIELDS,
            )
            csvw.writeheader()
            for repeater in filter_repeaters(repeaters, zone):
                csvw.writerow(
                    repeater_to_k7abd_row(
                        repeater, zone_name=name, name_format=name_format
                    )
                )
                total_channels += 1
        logger.debug(
            "Generate '%s' k7abd zones (%s channels) to '%s'",
            name,
            total_channels,
            out_file,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("proximity_csv_file", type=argparse.FileType("r"))
    parser.add_argument("output_dir")
    args = parser.parse_args()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    zones_to_k7abd(args.proximity_csv_file, args.output_dir)
