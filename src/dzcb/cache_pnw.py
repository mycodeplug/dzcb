"""
Cache PNWDigital Talkgroup HTML files to make testing easier
"""
import os
import sys
import time

import requests

from . import data
from . import pnwdigital_query_repeaters, pnwdigital_query_sites, DigitalRepeater

BASE = lambda p: os.path.join(os.path.dirname(data.__file__), "pnwdigital", p)

with open(BASE("repeaters.html"), "w") as f:
    html = pnwdigital_query_repeaters()
    sys.stderr.write(".")
    f.write(html.text)
with open(BASE("tgquery.html"), "w") as f:
    html = pnwdigital_query_sites()
    sys.stderr.write(".")
    f.write(html.text)
time.sleep(1)
repeaters = DigitalRepeater.from_html(html.text)
for r in repeaters:
    with open(BASE("{}.html").format(r._site_id), "w") as f:
        html = r.download_talkgroup_html()
        sys.stderr.write(".")
        f.write(html.text)
    time.sleep(0.25)
