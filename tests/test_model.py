from pathlib import Path
import os

import pytest

import dzcb.model


def csv_from_relative_dir(dname, fname):
    return (Path(os.path.dirname(__file__)) / dname / fname).read_text().splitlines()


def test_ordering_zones_only():
    o = dzcb.model.Ordering.from_csv(
        csv_from_relative_dir("model-ordering", "zones_only.csv")
    )
    assert len(o.contacts) == 0
    assert len(o.channels) == 0
    assert len(o.grouplists) == 0
    assert len(o.scanlists) == 0
    assert len(o.zones) == 3
    assert o.zones == ("A", "Z", "G")


def test_ordering_zones_contacts():
    o = dzcb.model.Ordering.from_csv(
        csv_from_relative_dir("model-ordering", "zones_contacts.csv")
    )
    assert len(o.contacts) == 2
    assert len(o.channels) == 0
    assert len(o.grouplists) == 0
    assert len(o.scanlists) == 0
    assert len(o.zones) == 4
    assert o.zones == ("Z", "Y", "W", "S")
    assert o.contacts == ("GF 1", "HG 2")


@pytest.fixture
def simple_codeplug():
    contacts = (
        dzcb.model.Talkgroup(
            "Foo", 0xF00, dzcb.model.ContactType.GROUP, dzcb.model.Timeslot.ONE
        ),
    )
    return dzcb.model.Codeplug(
        contacts=contacts,
        channels=(
            dzcb.model.AnalogChannel("Bar", "146.520", "6.0"),
            dzcb.model.DigitalChannel("Baz", "443.4375", "9", talkgroup=contacts[0]),
        ),
        grouplists=(dzcb.model.GroupList("Quuc", []),),
        scanlists=(dzcb.model.ScanList("Flar", []),),
        zones=(dzcb.model.Zone("ZigZag", [], []),),
    )


def test_Codeplug_filter(simple_codeplug):
    filtered = simple_codeplug.filter()
    assert len(filtered.contacts) == 1  # contacts are never pruned
    assert len(filtered.channels) == 2  # channels are never pruned
    assert len(filtered.grouplists) == 0  # empty grouplist is pruned
    assert len(filtered.scanlists) == 0  # empty scanlist is pruned
    assert len(filtered.zones) == 0  # empty zone is pruned


def test_Codeplug_filter_contacts(complex_codeplug):
    ct_filter = dzcb.model.Ordering(contacts=["CT1", "PC2"])
    include_cp = complex_codeplug.filter(include=ct_filter)
    assert len(include_cp.contacts) == 2
    assert len(include_cp.channels) == 7
    assert len(include_cp.grouplists) == 3
    assert len(include_cp.grouplists[0].contacts) == 2
    assert len(include_cp.grouplists[1].contacts) == 1
    assert len(include_cp.grouplists[2].contacts) == 1
    assert len(include_cp.scanlists) == 3
    assert len(include_cp.scanlists[0].channels) == 7
    assert len(include_cp.scanlists[1].channels) == 3
    assert len(include_cp.scanlists[2].channels) == 4
    assert len(include_cp.zones) == 4

    exclude_cp = complex_codeplug.filter(exclude=ct_filter)
    assert len(exclude_cp.contacts) == 4
    assert len(exclude_cp.channels) == 8
    assert len(exclude_cp.grouplists) == 3
    assert len(exclude_cp.grouplists[0].contacts) == 4
    assert len(exclude_cp.grouplists[1].contacts) == 2
    assert len(exclude_cp.grouplists[2].contacts) == 2
    assert len(exclude_cp.scanlists) == 3
    assert len(exclude_cp.scanlists[0].channels) == 8
    assert len(exclude_cp.scanlists[1].channels) == 3
    assert len(exclude_cp.scanlists[2].channels) == 5
    assert len(exclude_cp.zones) == 4


def test_Codeplug_order_contacts(complex_codeplug):
    ct_order = dzcb.model.Ordering(contacts=["CT3", "CT2", "PC3"])
    order_cp = complex_codeplug.filter(order=ct_order)
    assert list(ct.name for ct in order_cp.contacts) == [
        "CT3",
        "CT2",
        "PC3",
        "CT1",
        "PC1",
        "PC2",
    ]
    rorder_cp = complex_codeplug.filter(reverse_order=ct_order)
    assert list(ct.name for ct in rorder_cp.contacts) == [
        "CT1",
        "PC1",
        "PC2",
        "PC3",
        "CT2",
        "CT3",
    ]


def test_Channel_include_exclude(complex_codeplug):
    ch_include_A = complex_codeplug.filter(
        include=dzcb.model.Ordering(channels=["A.*"])
    )
    assert list(ch.name for ch in ch_include_A.channels) == ["A1", "A2", "A3"]
    assert list(zn.name for zn in ch_include_A.zones) == ["Z_ALL", "Z_A", "Z_A_D"]
    ch_exclude_2 = complex_codeplug.filter(
        exclude=dzcb.model.Ordering(channels=[".*2"])
    )
    assert list(ch.name for ch in ch_exclude_2.channels) == [
        "A1",
        "A3",
        "D1",
        "D3",
        "DR1",
        "DR3",
    ]


def test_Zone_include_exclude(complex_codeplug):
    # include doesn't imply ordering
    zn_include_A = complex_codeplug.filter(
        include=dzcb.model.Ordering(zones=["Z_A_D", "Z_A$"])
    )
    assert list(zn.name for zn in zn_include_A.zones) == ["Z_A", "Z_A_D"]
    assert list(
        dict((ch.name, ch) for zn in zn_include_A.zones for ch in zn.unique_channels)
    ) == ["A1", "A2", "A3", "D1", "D2", "D3"]
    zn_exclude_A = complex_codeplug.filter(
        exclude=dzcb.model.Ordering(zones=["Z_ALL", "Z_A", "Z_A_D"])
    )
    assert list(ch.name for zn in zn_exclude_A.zones for ch in zn.unique_channels) == [
        "D1",
        "D2",
        "D3",
        "DR1",
        "DR2",
        "DR3",
    ]
    assert list(zn.name for zn in zn_exclude_A.zones) == ["Z_D"]


@pytest.fixture(scope="session")
def replacements():
    return dzcb.model.Replacements.from_csv(
        csv_from_relative_dir("model-replacements", "replacements.csv")
    )


def names(l):
    return tuple(o.name for o in l)


def test_replacements(complex_codeplug, replacements):
    assert replacements.contacts == (("^CT([1-2])$", "ct\\1"),)
    assert replacements.channels == (("A", "a"),)
    assert replacements.grouplists == (
        ("GROP", "not found"),
        ("GL_", "gl_"),
        ("gl_", "g_L_"),
    )
    assert replacements.scanlists == (("_A$", "_analog"),)
    assert replacements.zones == (("_A(_)?", "_a\\1"),)
    rcp = complex_codeplug.filter(replacements=replacements)
    assert names(rcp.contacts) == ("ct1", "ct2", "CT3", "PC1", "PC2", "PC3")
    assert names(rcp.channels) == (
        "a1",
        "a2",
        "a3",
        "D1",
        "D2",
        "D3",
        "DR1",
        "DR2",
        "DR3",
    )
    assert names(rcp.grouplists) == ("g_L_ALL", "g_L_GRP", "g_L_PRV")
    assert names(rcp.scanlists) == ("SL_ALL", "SL_analog", "SL_D")
    assert names(rcp.zones) == ("Z_aLL", "Z_a", "Z_D", "Z_a_D")


def test_Channel_exclude_replacements(complex_codeplug):
    ch_exclude_A = complex_codeplug.filter(
        exclude=dzcb.model.Ordering(channels=["A", "d3", "dr2", "digitalrepeater3"]),
        replacements=dzcb.model.Replacements(channels=(("DR", "DigitalRepeater"),)),
    )
    assert list(ch.name for ch in ch_exclude_A.channels) == [
        "D1",
        "D2",
        "DigitalRepeater1",
    ]


def test_Grouplist_replacements(complex_codeplug):
    old = "GL_ALL"
    new = "gl_all"
    gl_replacements = complex_codeplug.filter(
        include=dzcb.model.Ordering(channels=["D1"]),
        replacements=dzcb.model.Replacements(grouplists=((old, new),)),
    )
    assert gl_replacements.channels[0].grouplist_name(complex_codeplug) == old
    assert gl_replacements.channels[0].grouplist_name(gl_replacements) == new


def test_Contact_replacements(complex_codeplug):
    ct_replacements = complex_codeplug.filter(
        replacements=dzcb.model.Replacements(contacts=(("CT1", "ContactOne"),)),
        include=dzcb.model.Ordering(contacts=["ContactOne", "CT2"]),
        exclude=dzcb.model.Ordering(channels=["A"]),
    )
    assert [ch.name for ch in ct_replacements.channels] == ["D1", "D2", "DR1", "DR2"]
    assert ct_replacements.channels[0].talkgroup.name == "ContactOne"
    assert ct_replacements.channels[1].talkgroup.name == "CT2"
    assert [tg.name for tg in ct_replacements.channels[2].static_talkgroups] == [
        "ContactOne",
        "CT2",
    ]
    assert [tg.name for tg in ct_replacements.channels[3].static_talkgroups] == [
        "ContactOne",
        "CT2",
    ]


def test_lookup_table_regen(complex_codeplug):
    with pytest.raises(KeyError):
        complex_codeplug.lookup("foo")
    assert complex_codeplug._lookup_table is not None
    new_cp = complex_codeplug.filter()
    assert new_cp._lookup_table is None
    assert complex_codeplug._lookup_table is not None
