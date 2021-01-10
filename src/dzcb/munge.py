"""
dzcb.munge - replacements, filters, and modifications of the data
"""
import re

# These are used when generating channel names
Talkgroup_Channel_name_replacements = {
    "Audio Test": "A.Test",
    "California": "CA",
    "English": "Eng",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Montana": "MT",
    "Oregon": "OR",
    "Utah": "UT",
    "Washington": "WA",
    "Worldwide": "WW",
}

def channel_name(ch_name, max_length):
    # Replace Long strings with shorter ones
    replacements = Talkgroup_Channel_name_replacements.copy()
    for find, repl in replacements.items():
        ch_name = ch_name.replace(find, repl)

    
    # Truncate the channel name (try to preserve the tail  characters
    # which are typically TG# and 3-digit Code)
    tail_code = re.search(r"[12]?\s[A-Z]+$", ch_name)
    if len(ch_name) > max_length and tail_code:
        n_tail = len(tail_code.group())
        if max_length > n_tail + 1:
            n_trunc = len(ch_name) - max_length
            ch_name = ch_name[:-n_trunc-n_tail] + ch_name[-n_tail:]

    return ch_name[:max_length]


def zone_name(zone_name, max_length):
    return zone_name[:max_length]


def ordered(seq, order, key=None):
    NotFound = object()
    head = [NotFound] * len(order)
    tail = []
    for item in seq:
        k = key(item) if key else item
        try:
            head[order.index(k)] = item
        except ValueError:
            tail.append(item)
    if NotFound in head:
        # XXX: print? really?
        print(
            "Items were not in the sequence to be ordered: {}".format(
                [order[ix] for ix, item in enumerate(head) if item is NotFound]
            )
        )
        head = [item for item in head if item is not NotFound]
    return head + tail
