"""
dzcb.munge - replacements, filters, and modifications of the data
"""
import re
import warnings


def channel_name(ch_name, max_length):
    # Truncate the channel name (try to preserve the tail  characters
    # which are typically TG# and 3-digit Code)
    tail_code = re.search(r"[12]?\s[A-Z]+$", ch_name)
    if len(ch_name) > max_length and tail_code:
        n_tail = len(tail_code.group())
        if max_length > n_tail + 1:
            n_trunc = len(ch_name) - max_length
            ch_name = ch_name[: -n_trunc - n_tail] + ch_name[-n_tail:]

    return ch_name[:max_length].strip()


def contact_name(contact_name):
    # PNWDigital source annoyinging appends "-2" to the TAC talkgroup names
    # strip off the suffix because not all systems have the TACs on TS 2
    # Radios such as the 868 can only map a given DMR ID to a single name
    # so the "-2" suffix is confusing
    if contact_name.startswith("TAC") and contact_name.endswith("-2"):
        return contact_name[:-2]
    return contact_name


def zone_name(zone_name, max_length):
    return zone_name[:max_length]


class MissingItemsWarning(UserWarning):
    """Raised when items in order list do not appear in the sequence"""

    def __init__(self, missing_items, sequence, log_sequence_name=None):
        self.sequence = sequence
        self.missing_items = missing_items
        if log_sequence_name is None:
            log_sequence_name = "the sequence to be ordered"
        self.log_sequence_name = log_sequence_name

    def __str__(self):
        return "Items were not in {}: {}".format(
            self.log_sequence_name, self.missing_items
        )


def ordered(seq, order, key=None, log_sequence_name=None, reverse=False):
    """
    If `log_sequence_name` is specified, use that text instead of
    "the sequence to be ordered" when emitting a log message about
    missing items.
    """
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
        warnings.warn(
            MissingItemsWarning(
                missing_items=[
                    order[ix] for ix, item in enumerate(head) if item is NotFound
                ],
                sequence=seq,
                log_sequence_name=log_sequence_name,
            ),
            stacklevel=2,
        )
        head = [item for item in head if item is not NotFound]
    if reverse:
        head.reverse()
        return tail + head
    return head + tail


def ordered_re(seq, order_regexs, key=None, reverse=False):
    """
    Order the sequence preferring items that match regexes.

    If the regex matches multiple items, the matched subsequence will retain its natural order.
    """
    head = []
    tail = list(seq)
    table = tuple(item if key is None else key(item) for item in seq)
    found_indexes = set()
    for p in (re.compile(p, re.IGNORECASE) for p in order_regexs):
        for ix, k in enumerate(table):
            if ix not in found_indexes and p.match(k):
                head.append(seq[ix])
                found_indexes.add(ix)
    for ix in sorted(found_indexes, reverse=True):
        del tail[ix]
    if reverse:
        head.reverse()
        return tail + head
    return head + tail
