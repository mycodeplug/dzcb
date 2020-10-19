"""
Cache PNWDigital Talkgroup HTML files to make testing easier
"""
import sys
import time

import requests

from . import pnwdigital_query_repeaters, DigitalRepeater


with open("repeaters.html", "w") as f:
    html = pnwdigital_query_repeaters()
    sys.stderr.write(".")
    f.write(html.text)
time.sleep(1)
repeaters = DigitalRepeater.from_html(html.text)
for r in repeaters:
    with open("{}.html".format(r._site_id), "w") as f:
        html = r.download_talkgroup_html()
        sys.stderr.write(".")
        f.write(html.text)
    time.sleep(0.25)
