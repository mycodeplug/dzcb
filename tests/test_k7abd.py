import os
from pathlib import Path

import pytest

from dzcb import k7abd
from dzcb.model import Contact, Timeslot


@pytest.fixture(autouse=True)
def reset_dzcb_model_Contact__all_contacts_by_id():
    saved = Contact._all_contacts_by_id
    Contact._all_contacts_by_id = {}
    yield
    Contact._all_contacts_by_id = saved


def codeplug_from_relative_dir(dname):
    input_dir = Path(os.path.dirname(__file__)) / dname
    return k7abd.Codeplug_from_k7abd(input_dir)


def test_multiple_repeaters_one_talkgroups():
    """
    a Digital-Repeaters__ZoneName.csv files does NOT require a Talkgroups__ZoneName.csv
    file, as long as all of the talkgroups are defined in at least one
    existing Talkgroups.csv
    """

    cp = codeplug_from_relative_dir("multiple-repeaters-one-talkgroups")
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


def test_digital_repeaters_missing_talkgroup():
    """
    Unknown talkgroup names in Digital-Repeaters__ZoneName.csv
    will be ignored in the generated codeplug.
    """

    cp = codeplug_from_relative_dir("digital-repeaters-missing-talkgroup")
    assert len(cp.zones) == 1
    assert len(cp.contacts) == 1
    assert len(cp.channels) == 1

    assert cp.channels[0].name == "Foo"
    stg0 = cp.channels[0].static_talkgroups[0]
    assert stg0.name == "TG 2"
    assert stg0.dmrid == 2
    assert stg0.timeslot == Timeslot.ONE


def test_digital_channels_missing_talkgroup():
    """
    Unknown talkgroup names in Digital-Others__ZoneName.csv
    will be ignored in the generated codeplug.
    """

    cp = codeplug_from_relative_dir("digital-channels-missing-talkgroup")
    assert len(cp.zones) == 1
    assert len(cp.contacts) == 1
    assert len(cp.channels) == 1

    assert cp.channels[0].name == "Bar TG 2"
    ch0tg = cp.channels[0].talkgroup
    assert ch0tg.name == "TG 2"
    assert ch0tg.dmrid == 2
    assert ch0tg.timeslot == Timeslot.ONE