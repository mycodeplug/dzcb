import pstats
import sys

p = pstats.Stats(sys.argv[1])
p.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(15)
