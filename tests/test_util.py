import pytest

import dzcb.util


ENV_VAR_NAME = "TEST_UTIL_ENVVAR"


@pytest.fixture(
    params=[
        ("yes", True),
        ("on", True),
        (0, False),
        ("no", False),
        ("off", False),
        (None, None),  # should use default
        ("foo", KeyError),  # should use default
    ]
)
def exp_env_bool(request, monkeypatch):
    env_value, exp_bool_value = request.param
    if env_value is not None:
        monkeypatch.setenv(ENV_VAR_NAME, env_value)
    return exp_bool_value


@pytest.mark.parametrize("default", [True, False])
def test_getenv_bool(exp_env_bool, default):
    if isinstance(exp_env_bool, type) and issubclass(exp_env_bool, Exception):
        with pytest.raises(exp_env_bool):
            _ = dzcb.util.getenv_bool(ENV_VAR_NAME, default=default)
        return

    val = dzcb.util.getenv_bool(ENV_VAR_NAME, default=default)
    if exp_env_bool is None:
        assert val is default
    else:
        assert val is exp_env_bool
