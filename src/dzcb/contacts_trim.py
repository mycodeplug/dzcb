"""
dzcb.contacts_trim - remove contacts to get under radio limits
"""
import sys

remove_suffixes = [
    ",",
    ",GR",
    ",CY",
    ",CN",
    ",BE",
    ",FR",
    ",ES",
    ",IT",
    ",RU",
    ",PL",
    ",DE",
    ",PT",
    ",TR",
    ",SI",
    ",JP",
    ",Korea Republic of",
    ",PH",
    ",MY",
    ",TH",
    ",AR",
    ",BR",
    ",CL",
    ",CO",
    ",VE",
    ",UY",
    ",SE",
    ",CH",
    ",CZ",
    ",SK",
    "BA",
    "HR",
    "AT",
]

total = 0


def check_suffix(line):
    for s in remove_suffixes:
        if line.strip().endswith(s):
            return None
    return line


for line in sys.stdin:
    outline = check_suffix(line)
    if outline:
        total += 1
        sys.stdout.write(outline)

sys.stderr.write(f"Wrote {total} records")
