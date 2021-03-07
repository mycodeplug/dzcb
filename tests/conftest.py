import pytest

import dzcb.model


@pytest.fixture(scope="session")
def complex_codeplug():
    contacts = (
        dzcb.model.Talkgroup("CT1", 0xF01, dzcb.model.ContactType.GROUP, timeslot=1),
        dzcb.model.Talkgroup("CT2", 0xF02, dzcb.model.ContactType.GROUP, timeslot=2),
        dzcb.model.Talkgroup("CT3", 0xF03, dzcb.model.ContactType.GROUP, timeslot=1),
        dzcb.model.Talkgroup("PC1", 0xE01, dzcb.model.ContactType.PRIVATE, timeslot=1),
        dzcb.model.Talkgroup("PC2", 0xE02, dzcb.model.ContactType.PRIVATE, timeslot=2),
        dzcb.model.Talkgroup("PC3", 0xE03, dzcb.model.ContactType.PRIVATE, timeslot=1),
    )
    grouplists = (
        dzcb.model.GroupList("GL_ALL", contacts[:]),
        dzcb.model.GroupList("GL_GRP", contacts[:3]),
        dzcb.model.GroupList("GL_PRV", contacts[3:]),
    )
    channels = (
        dzcb.model.AnalogChannel("A1", "146.520", "6.0"),
        dzcb.model.AnalogChannel("A2", "146.530", "6.0"),
        dzcb.model.AnalogChannel("A3", "146.540", "6.0"),
        dzcb.model.DigitalChannel(
            "D1", "443.4375", "9", talkgroup=contacts[0], grouplist=grouplists[0]
        ),
        dzcb.model.DigitalChannel(
            "D2", "443.4375", "9", talkgroup=contacts[1], grouplist=grouplists[1]
        ),
        dzcb.model.DigitalChannel(
            "D3", "443.4375", "9", talkgroup=contacts[2], grouplist=grouplists[1]
        ),
        dzcb.model.DigitalChannel(
            "DR1",
            "443.4375",
            "9",
            static_talkgroups=contacts[:],
            grouplist=grouplists[1],
        ),
        dzcb.model.DigitalChannel(
            "DR2",
            "444.4375",
            "9",
            static_talkgroups=[contacts[0], contacts[1]],
            grouplist=grouplists[1],
        ),
        dzcb.model.DigitalChannel(
            "DR3",
            "445.4375",
            "9",
            static_talkgroups=[contacts[3], contacts[4]],
            grouplist=grouplists[2],
        ),
    )
    scanlists = (
        dzcb.model.ScanList("SL_ALL", channels[:]),
        dzcb.model.ScanList("SL_A", channels[:3]),
        dzcb.model.ScanList("SL_D", channels[3:]),
    )
    zones = (
        dzcb.model.Zone("Z_ALL", channels[:], channels[:]),
        dzcb.model.Zone("Z_A", channels[:3], channels[:3]),
        dzcb.model.Zone("Z_D", channels[3:], channels[3:]),
        dzcb.model.Zone("Z_A_D", channels[:3], channels[3:6]),
    )
    return dzcb.model.Codeplug(
        contacts=contacts,
        channels=channels,
        grouplists=grouplists,
        scanlists=scanlists,
        zones=zones,
    )