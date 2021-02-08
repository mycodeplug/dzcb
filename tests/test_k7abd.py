import os
from pathlib import Path

from dzcb import k7abd
from dzcb.model import Timeslot


def test_multiple_repeaters_one_talkgroups():
    """
    a Digital-Repeaters__ZoneName.csv files does NOT require a Talkgroups__ZoneName.csv
    file, as long as all of the talkgroups are defined in at least one
    existing Talkgroups.csv
    """

    input_dir = Path(os.path.dirname(__file__)) / "multiple-repeaters-one-talkgroups"
    cp = k7abd.Codeplug_from_k7abd(input_dir)
    assert len(cp.zones) == 2
    assert len(cp.contacts) == 3
    assert len(cp.channels) == 2

    exp_cp = cp.expand_static_talkgroups()
    assert len(exp_cp.zones) == 2
    assert len(exp_cp.contacts) == 3
    assert len(exp_cp.channels) == 6

    expect_channels = [
        ("Simplex 99 2 BAR", "Simplex 99", Timeslot.TWO),
        ("TG 2 BAR", "TG 2", Timeslot.TWO),
        ("TG 9 2 BAR", "TG 9", Timeslot.TWO),
        ("Simplex 99 1 FOO", "Simplex 99", Timeslot.ONE),
        ("TG 2 1 FOO", "TG 2", Timeslot.ONE),
        ("TG 9 1 FOO", "TG 9", Timeslot.ONE),
    ]

    for ch, exp_ch in zip(exp_cp.channels, expect_channels):
        assert ch.name == exp_ch[0]
        assert ch.talkgroup.name == exp_ch[1]
        assert ch.talkgroup.timeslot == exp_ch[2]
