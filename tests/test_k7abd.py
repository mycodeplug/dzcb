import json
import os
from pathlib import Path

import pytest

from dzcb import farnsworth, k7abd
from dzcb.model import Timeslot, ContactType


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
    assert len(cp.contacts) == 6
    assert len(cp.channels) == 2

    expanded_cp = cp.expand_static_talkgroups()
    assert len(expanded_cp.zones) == 2
    assert len(expanded_cp.contacts) == 6
    assert len(expanded_cp.channels) == 6

    expect_channels = [
        ("Simplex 99 2 BAR", "Simplex 99", Timeslot.TWO),
        ("TG 2 BAR", "TG 2", Timeslot.TWO),
        ("TG 9 2 BAR", "TG 9", Timeslot.TWO),
        ("Simplex 99 1 FOO", "Simplex 99", Timeslot.ONE),
        ("TG 2 1 FOO", "TG 2", Timeslot.ONE),
        ("TG 9 1 FOO", "TG 9", Timeslot.ONE),
    ]

    print("EXPECT CHANNELS:\n{}".format("\n".join(str(ch) for ch in expect_channels)))
    print(
        "ACTUAL CHANNELS:\n{}".format("\n".join(str(ch) for ch in expanded_cp.channels))
    )

    for ch, exp_ch in zip(expanded_cp.channels, expect_channels):
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


@pytest.fixture(params=[True, False])
def require_valid_tone(request, monkeypatch):
    import dzcb.tone

    monkeypatch.setattr(dzcb.tone, "REQUIRE_VALID_TONE", request.param)
    return request.param


def test_analog_weird_values(require_valid_tone):
    """
    test validation of fields in the csv file
    """

    cp = codeplug_from_relative_dir("analog-weird-values").filter()

    assert len(cp.zones) == 6 if require_valid_tone else 9
    assert len(cp.channels) == 6 if require_valid_tone else 9

    for ch in cp.channels:
        if ch.name in ("off", "blank"):
            assert ch.tone_decode is None
            assert ch.tone_encode is None
        elif ch.name == "lowerd023":
            assert ch.tone_decode == "D023"
            assert ch.tone_encode == "D023"
        elif ch.name == "sixty-seven":
            assert ch.tone_decode == "67.0"
            assert ch.tone_encode == "67.0"
        elif ch.name == "sixty-seven-decimal":
            assert ch.tone_decode == "67.0"
            assert ch.tone_encode == "67.0"
        elif ch.name == "split-tone":
            assert ch.tone_decode == "74.4"
            assert ch.tone_encode == "254.1"
        if require_valid_tone:
            assert ch.name != "restricted-in"
            assert ch.name != "restricted-out"
            assert ch.name != "sixty-nine"
        else:
            if ch.name == "restricted-in":
                assert ch.tone_decode == "restricted"
                assert ch.tone_encode is None
            elif ch.name == "restricted-out":
                assert ch.tone_decode is None
                assert ch.tone_encode == "restricted"
            elif ch.name == "sixty-nine":
                assert ch.tone_decode == "69.0"
                assert ch.tone_encode == "69.0"


def test_digital_repeaters_private_contacts():
    """
    Private contacts in Digital-Repeaters__ZoneName.csv
    """

    cp = codeplug_from_relative_dir("talkgroups-private")
    assert len(cp.zones) == 1
    assert len(cp.contacts) == 4
    assert len(cp.channels) == 1

    assert cp.channels[0].name == "Foo"
    assert [
        (st.name, st.dmrid, st.timeslot, st.kind)
        for st in cp.channels[0].static_talkgroups
    ] == [
        ("BM Parrot", 9990, Timeslot.ONE, ContactType.PRIVATE),
        ("Disconnect", 4000, Timeslot.ONE, ContactType.PRIVATE),
        ("Parrot", 9998, Timeslot.ONE, ContactType.GROUP),
        ("Private Parrot", 9998, Timeslot.ONE, ContactType.PRIVATE),
    ]


def test_digital_repeaters_same_tg_different_ts():
    """
    A talkgroup may be carried on either timeslot.
    """

    cp = codeplug_from_relative_dir("digital-repeaters-same-tg-different-ts")
    assert len(cp.zones) == 2
    assert len(cp.contacts) == 2
    assert len(cp.channels) == 3

    expanded_cp = cp.expand_static_talkgroups()
    assert len(expanded_cp.zones) == 3
    assert len(expanded_cp.contacts) == 2
    assert len(expanded_cp.channels) == 3

    expect_channels = [
        ("PNW Rgnl 2 DHS", "PNW Rgnl", Timeslot.TWO),
        ("PNW Rgnl 2 1 MMB", "PNW Rgnl 2", Timeslot.ONE),
        ("PNW Rgnl 2 MOF", "PNW Rgnl 2", Timeslot.TWO),
    ]

    print("EXPECT CHANNELS:\n{}".format("\n".join(str(ch) for ch in expect_channels)))
    print(
        "ACTUAL CHANNELS:\n{}".format("\n".join(str(ch) for ch in expanded_cp.channels))
    )

    for ch, exp_ch in zip(expanded_cp.channels, expect_channels):
        assert ch.name == exp_ch[0]
        assert ch.talkgroup.name == exp_ch[1]
        assert ch.talkgroup.timeslot == exp_ch[2]

    # farnsworth output collapses talkgroups by ID, so only 1 FW contact should be generated
    # for the 2 contacts in the codeplug
    fw_cp = json.loads(farnsworth.Codeplug_to_json(expanded_cp))
    assert len(fw_cp["Contacts"]) == 1
    tg_name = fw_cp["Contacts"][0]["Name"]
    assert len(fw_cp["Channels"]) == 3
    for channel in fw_cp["Channels"]:
        assert channel["ContactName"] == tg_name

    assert len(fw_cp["GroupLists"]) == 3
    for grouplist in fw_cp["GroupLists"]:
        assert grouplist["Contact"] == [tg_name]
