"""
dzcb.contacts_trim - remove contacts to get under radio limits
"""
import argparse
import csv
import json
from pathlib import Path
import time
import sys

import requests

from dzcb import appdir

RADIO_ID_USERS_JSON = "https://database.radioid.net/static/users.json"
RADIO_ID_USERS_MAX_AGE = 3600 * 12.1


total = 0


def cached_json(url, max_age=RADIO_ID_USERS_MAX_AGE):
    cachedir = Path(appdir.user_cache_dir)
    filepath = cachedir / "usersdb.json"
    if not filepath.exists() or filepath.stat().st_mtime < time.time() - max_age:
        # cache is expired, need to refetch
        cachedir.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url)
        filepath.write_bytes(resp.content)
    return filepath


def group_users_by(field_name):
    groups = {}
    with open(cached_json(RADIO_ID_USERS_JSON)) as f:
        db = json.load(f)
        for user in db["users"]:
            groups.setdefault(user[field_name].lower(), []).append(user)
    return groups


def flatten_groups(groups):
    users = []
    for ulist in groups.values():
        users.extend(ulist)
    return users


def users_to_md_uv380_csv(users, output):
    fields = ["radio_id", "callsign", "fname", "city", "state", "remarks", "country"]
    with open(output, "w", newline="") as out:
        csvw = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        for u in users:
            u["fname"] = u["fname"].partition(" ")[0].capitalize()
            u["city"] = u["city"].capitalize()
            u["state"] = u["state"].capitalize()
            u["remarks"] = ""
            csvw.writerow(u)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_file")
    args = parser.parse_args()
    users_by_country = group_users_by("country")
    filtered = users_by_country["united states"] + users_by_country["canada"]
    users_to_md_uv380_csv(filtered, args.output_file)
    sys.stderr.write(f"Wrote {len(filtered)} records")
