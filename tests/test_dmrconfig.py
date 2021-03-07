from importlib_resources import files

import pytest

import dzcb.output.dmrconfig
import dzcb.data


default_dmrconfig_path = files(dzcb.data) / "dmrconfig"


@pytest.mark.parametrize(
    "template",
    (pytest.param(tf.read_text(), id=tf.name) for tf in default_dmrconfig_path.glob("*.conf")),
)
def test_dmrconfig_templates(complex_codeplug, template):
    table = dzcb.output.dmrconfig.Table(complex_codeplug)
    assert dzcb.output.dmrconfig.Dmrconfig_Codeplug(table, template).render_template()