from . import DigitalRepeater, pnwdigital_query_repeaters, write_talkgroup_matrix

import sys

outfile = sys.argv[1]

repeaters = DigitalRepeater.from_cache_all()
with open(outfile, "w") as f:
    write_talkgroup_matrix(repeaters, f)
print("Output written to {}".format(outfile))
