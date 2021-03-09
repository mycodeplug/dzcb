from importlib_resources import files

import pytest

import dzcb.model
import dzcb.output.dmrconfig
import dzcb.data


default_dmrconfig_path = files(dzcb.data) / "dmrconfig"


@pytest.mark.parametrize(
    "template",
    (
        pytest.param(tf.read_text(), id=tf.name)
        for tf in default_dmrconfig_path.glob("*.conf")
    ),
)
def test_dmrconfig_templates(complex_codeplug, template):
    table = dzcb.output.dmrconfig.Table(complex_codeplug)
    assert dzcb.output.dmrconfig.Dmrconfig_Codeplug(table, template).render_template()


@pytest.fixture
def same_contact_both_timeslots_codeplug():
    """
    regression test for #65

    1 contact used on 2 different timeslots will result in arbitrary missing channels
    """

    ct = dzcb.model.Contact(
        name="CT",
        dmrid=1,
    )
    tg_1 = dzcb.model.Talkgroup.from_contact(ct, timeslot=dzcb.model.Timeslot.ONE)
    tg_2 = dzcb.model.Talkgroup.from_contact(ct, timeslot=dzcb.model.Timeslot.TWO)

    ch = dzcb.model.DigitalChannel(
        name="RP", frequency="444.444", static_talkgroups=[tg_1, tg_2]
    )

    zn = dzcb.model.Zone(
        name="ZN",
        channels_a=[ch],
        channels_b=[ch],
    )

    return dzcb.model.Codeplug(
        contacts=[tg_1, tg_2],
        channels=[ch],
        zones=[zn],
    )


def test_dmrconfig_contact_integrity(same_contact_both_timeslots_codeplug):
    cp = same_contact_both_timeslots_codeplug
    assert len(cp.channels) == 1

    exp_cp = cp.expand_static_talkgroups()
    exp_channel_names = ("CT 1 RP", "CT 2 RP")
    assert tuple(ch.name for ch in exp_cp.channels) == exp_channel_names

    dmrconfig_cp = dzcb.output.dmrconfig.Dmrconfig_Codeplug(
        table=dzcb.output.dmrconfig.Table(codeplug=exp_cp),
    )

    dmrconfig_conf = "\n".join(dmrconfig_cp.render())
    for ch_name in exp_channel_names:
        assert ch_name.replace(" ", "_") in dmrconfig_conf
