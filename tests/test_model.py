from pathlib import Path
import os

import dzcb.model


def csv_from_relative_dir(dname, fname):
    return (Path(os.path.dirname(__file__)) / dname / fname).read_text().splitlines()


def test_ordering_zones_only():
    o = dzcb.model.Ordering.from_csv(csv_from_relative_dir("model-ordering", "zones_only.csv"))
    assert len(o.contacts) == 0
    assert len(o.channels) == 0
    assert len(o.grouplists) == 0
    assert len(o.scanlists) == 0
    assert len(o.zones) == 3
    assert o.zones == ["A", "Z", "G"]


def test_ordering_zones_contacts():
    o = dzcb.model.Ordering.from_csv(csv_from_relative_dir("model-ordering", "zones_contacts.csv"))
    assert len(o.contacts) == 2
    assert len(o.channels) == 0
    assert len(o.grouplists) == 0
    assert len(o.scanlists) == 0
    assert len(o.zones) == 4
    assert o.zones == ["Z", "Y", "W", "S"]
    assert o.contacts == ["GF 1", "HG 2"]
