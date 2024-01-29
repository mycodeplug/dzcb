import pytest

import dzcb.model
import dzcb.farnsworth


@pytest.fixture
def supported_admit_criteria_codeplug():
    """
    Minimal code plug channels for each admit criteria supported
    by Farnsworth codeplugs.
    """

    ct = dzcb.model.Contact(
        name="CT",
        dmrid=1,
    )
    tg_1 = dzcb.model.Talkgroup.from_contact(ct, timeslot=dzcb.model.Timeslot.ONE)

    chs = [
        dzcb.model.DigitalChannel(
            name=ac.value, frequency="444.444", static_talkgroups=[tg_1],
            admit_criteria=ac,
        )
        for ac in dzcb.farnsworth.AdmitCriteria_map
    ]

    zn = dzcb.model.Zone(
        name="ZN",
        channels_a=chs,
        channels_b=chs,
    )

    return dzcb.model.Codeplug(
        contacts=[tg_1],
        channels=chs,
        zones=[zn],
    )


def test_farnsworth_admit_criteria(supported_admit_criteria_codeplug):
    """
    Verify that a codeplug using all admit criteria supported by
    Farnsworth codeplugs can be converted without error.
    """

    cp = supported_admit_criteria_codeplug
    assert len(cp.channels) > 0

    exp_cp = cp.expand_static_talkgroups()
    json = dzcb.farnsworth.Codeplug_to_json(exp_cp)


@pytest.fixture
def unsupported_admit_criteria_codeplug():
    """
    Minimal code plug with a channel with admit criteria that is not supported by editcp.
    """

    ct = dzcb.model.Contact(
        name="CT",
        dmrid=1,
    )
    tg_1 = dzcb.model.Talkgroup.from_contact(ct, timeslot=dzcb.model.Timeslot.ONE)

    ch = dzcb.model.DigitalChannel(
        name="RP", frequency="444.444", static_talkgroups=[tg_1],
        admit_criteria=dzcb.model.AdmitCriteria.DIFFERENT_COLOR,
    )

    zn = dzcb.model.Zone(
        name="ZN",
        channels_a=[ch],
        channels_b=[ch],
    )

    return dzcb.model.Codeplug(
        contacts=[tg_1],
        channels=[ch],
        zones=[zn],
    )


def test_farnsworth_unsupported_admit_criteria(unsupported_admit_criteria_codeplug):
    cp = unsupported_admit_criteria_codeplug
    assert len(cp.channels) == 1

    exp_cp = cp.expand_static_talkgroups()

    with pytest.raises(ValueError):
        dzcb.farnsworth.Codeplug_to_json(exp_cp)
