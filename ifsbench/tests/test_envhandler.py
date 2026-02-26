# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for all classes that represent benchmark files
"""

from contextlib import nullcontext
import os

import pytest

from ifsbench.env import EnvHandler, EnvOperation, DefaultEnvPipeline


@pytest.mark.parametrize(
    "mode,key,value,success",
    [
        (EnvOperation.SET, "some_key", "some_value", True),
        (EnvOperation.SET, None, "some_value", False),
        (EnvOperation.SET, "some_key", None, True),
        (EnvOperation.SET, None, None, False),
        (EnvOperation.DELETE, "some_key", "some_value", True),
        (EnvOperation.DELETE, None, "some_value", False),
        (EnvOperation.DELETE, "some_key", None, True),
        (EnvOperation.DELETE, None, None, False),
        (EnvOperation.APPEND, "some_key", "some_value", True),
        (EnvOperation.APPEND, None, "some_value", False),
        (EnvOperation.APPEND, "some_key", None, False),
        (EnvOperation.APPEND, None, None, False),
        (EnvOperation.PREPEND, "some_key", "some_value", True),
        (EnvOperation.PREPEND, None, "some_value", False),
        (EnvOperation.PREPEND, "some_key", None, False),
        (EnvOperation.PREPEND, None, None, False),
        (EnvOperation.CLEAR, "some_key", "some_value", True),
        (EnvOperation.CLEAR, None, "some_value", True),
        (EnvOperation.CLEAR, "some_key", None, True),
        (EnvOperation.CLEAR, None, None, True),
    ],
)
def test_envhandler_init(mode, key, value, success):
    """
    Initialise the EnvHandler and make sure that only correct values are
    accepted.
    """

    if success:
        context = nullcontext()
    else:
        context = pytest.raises(ValueError)

    with context:
        EnvHandler(mode=mode, key=key, value=value)


@pytest.mark.parametrize(
    "mode,key,value,success",
    [
        (EnvOperation.SET, "some_key", "some_value", True),
        (EnvOperation.SET, None, "some_value", False),
        (EnvOperation.SET, "some_key", None, True),
        (EnvOperation.SET, None, None, False),
        (EnvOperation.DELETE, "some_key", "some_value", True),
        (EnvOperation.DELETE, None, "some_value", False),
        (EnvOperation.DELETE, "some_key", None, True),
        (EnvOperation.DELETE, None, None, False),
        (EnvOperation.APPEND, "some_key", "some_value", True),
        (EnvOperation.APPEND, None, "some_value", False),
        (EnvOperation.APPEND, "some_key", None, False),
        (EnvOperation.APPEND, None, None, False),
        (EnvOperation.PREPEND, "some_key", "some_value", True),
        (EnvOperation.PREPEND, None, "some_value", False),
        (EnvOperation.PREPEND, "some_key", None, False),
        (EnvOperation.PREPEND, None, None, False),
        (EnvOperation.CLEAR, "some_key", "some_value", True),
        (EnvOperation.CLEAR, None, "some_value", True),
        (EnvOperation.CLEAR, "some_key", None, True),
        (EnvOperation.CLEAR, None, None, True),
    ],
)
def test_envhandler_from_config_dump_config(mode, key, value, success):
    """
    Initialise the EnvHandler and make sure that only correct values are
    accepted.
    """

    if success:
        context = nullcontext()
    else:
        context = pytest.raises(ValueError)

    config = {
        "mode": mode,
    }
    if key:
        config["key"] = key
    if value:
        config["value"] = value
    with context:
        ev = EnvHandler.from_config(config)

    if success:
        conf_out = ev.dump_config()

        assert conf_out == config


@pytest.mark.parametrize(
    "mode,key,value,env_in,env_out",
    [
        (EnvOperation.SET, "some_key", "some_value", {}, {"some_key": "some_value"}),
        (
            EnvOperation.SET,
            "some_key",
            "new_value",
            {"some_key": "some_value"},
            {"some_key": "new_value"},
        ),
        (
            EnvOperation.SET,
            "some_key",
            None,
            {"some_key": "some_value"},
            {"some_key": None},
        ),
        (EnvOperation.DELETE, "some_key", None, {}, {}),
        (EnvOperation.DELETE, "some_key", "new_value", {"some_key": "some_value"}, {}),
        (EnvOperation.CLEAR, "some_key", None, {}, {}),
        (
            EnvOperation.CLEAR,
            None,
            None,
            {"some_key": "some_value", "other_key": None},
            {},
        ),
        (
            EnvOperation.APPEND,
            "some_list",
            "some_value",
            {},
            {"some_list": "some_value"},
        ),
        (
            EnvOperation.APPEND,
            "some_list",
            "new_value",
            {"some_list": "some_value"},
            {"some_list": "some_value" + os.pathsep + "new_value"},
        ),
        (
            EnvOperation.PREPEND,
            "some_list",
            "some_value",
            {},
            {"some_list": "some_value"},
        ),
        (
            EnvOperation.PREPEND,
            "some_list",
            "some_value",
            {"some_list": None},
            {"some_list": "some_value"},
        ),
        (
            EnvOperation.PREPEND,
            "some_list",
            "new_value",
            {"some_list": "some_value"},
            {"some_list": "new_value" + os.pathsep + "some_value"},
        ),
    ],
)
def test_envhandler_execute(mode, key, value, env_in, env_out):
    """
    Execute an EnvHandler and make sure that the output is correct.
    """
    handler = EnvHandler(mode=mode, key=key, value=value)
    env = {**env_in}

    handler.execute(env)

    assert env == {**env_out}


@pytest.mark.parametrize(
    "handler_data, env_in",
    [
        ((), {}),
        (
            (),
            {"some_value": None, "other_value": "2"},
        ),
        (
            (
                {"mode": EnvOperation.SET, "key": "some_value"},
                {
                    "mode": EnvOperation.CLEAR,
                },
                {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
            ),
            {},
        ),
        (
            (
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "end"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
        ),
        (
            (
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
        ),
        (
            (
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
                {"mode": EnvOperation.SET, "key": "some_list", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
        ),
        (
            (
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.SET, "key": "some_value", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path", "some_value": "3"},
        ),
    ],
)
def test_defaultenvpipeline_from_config(handler_data, env_in):
    """
    Execute an DefaultEnvPipeline and check the resulting environment.
    """

    config = {"handlers": handler_data, "env_initial": env_in}
    pipeline = DefaultEnvPipeline.from_config(config)

    assert len(pipeline.handlers) == len(handler_data)
    for i, h in enumerate(pipeline.handlers):
        assert isinstance(h, EnvHandler)
        assert h.mode == handler_data[i]["mode"]
        if "key" in handler_data[i]:
            assert h.key == handler_data[i]["key"]
        else:
            assert h.key is None
        if "value" in handler_data[i]:
            assert h.value == handler_data[i]["value"]
        else:
            assert h.value is None

    assert pipeline.env_initial == env_in


@pytest.mark.parametrize(
    "handler_data, env_in",
    [
        ([], {}),
        (
            [],
            {"some_value": None, "other_value": "2"},
        ),
        (
            [
                {"mode": EnvOperation.SET, "key": "some_value"},
                {
                    "mode": EnvOperation.CLEAR,
                },
                {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
            ],
            {},
        ),
        (
            [
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "end"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            {"some_list": "path"},
        ),
        (
            [
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            {"some_list": "path"},
        ),
        (
            [
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
                {"mode": EnvOperation.SET, "key": "some_list", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            {"some_list": "path"},
        ),
        (
            [
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.SET, "key": "some_value", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            {"some_list": "path", "some_value": "3"},
        ),
    ],
)
def test_defaultenvpipeline_dump_config(handler_data, env_in):
    """
    Execute an DefaultEnvPipeline and check the resulting environment.
    """

    pipeline = DefaultEnvPipeline(handlers=handler_data, env_initial=env_in)

    conf_out = pipeline.dump_config()

    expected = {"handlers": handler_data, "env_initial": env_in}
    assert conf_out == expected


@pytest.mark.parametrize(
    "handler_in, handler_add",
    [
        (
            [],
            {"mode": EnvOperation.SET, "key": "some_value"},
        ),
        (
            [
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "end"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
        ),
    ],
)
def test_defaultenvpipeline_add_single(handler_in, handler_add):

    ep = DefaultEnvPipeline(handlers=handler_in)

    ep.add(EnvHandler.from_config(handler_add))

    result = ep.handlers
    assert len(result) == len(handler_in) + 1
    expected = [*handler_in, handler_add]

    for i, h in enumerate(expected):
        assert result[i].dump_config() == h


@pytest.mark.parametrize(
    "handler_in, handler_add",
    [
        (
            [],
            [
                {"mode": EnvOperation.SET, "key": "some_value"},
                {
                    "mode": EnvOperation.CLEAR,
                },
                {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
            ],
        ),
        (
            [
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "end"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ],
            [
                {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
                {
                    "mode": EnvOperation.CLEAR,
                },
            ],
        ),
    ],
)
def test_defaultenvpipeline_add_list(handler_in, handler_add):

    ep = DefaultEnvPipeline(handlers=handler_in)

    additional = [EnvHandler.from_config(c) for c in handler_add]
    ep.add(additional)

    result = ep.handlers
    expected = handler_in + handler_add

    assert len(result) == len(expected)
    for i, h in enumerate(expected):
        assert result[i].dump_config() == h


@pytest.mark.parametrize(
    "handler_data, env_in, env_out",
    [
        ((), {}, {}),
        (
            (),
            {"some_value": None, "other_value": "2"},
            {"some_value": None, "other_value": "2"},
        ),
        (
            (
                {"mode": EnvOperation.SET, "key": "some_value"},
                {
                    "mode": EnvOperation.CLEAR,
                },
                {"mode": EnvOperation.SET, "key": "other_value", "value": "3"},
            ),
            {},
            {"other_value": "3"},
        ),
        (
            (
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "end"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
            {
                "some_list": "start"
                + os.pathsep
                + "path"
                + os.pathsep
                + "end"
                + os.pathsep
                + "endend"
            },
        ),
        (
            (
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.APPEND, "key": "some_list", "value": "endend"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
            {"some_list": "start" + os.pathsep + "endend"},
        ),
        (
            (
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
                {"mode": EnvOperation.SET, "key": "some_list", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path"},
            {"some_list": "start" + os.pathsep + "override"},
        ),
        (
            (
                {"mode": EnvOperation.DELETE, "key": "some_list"},
                {"mode": EnvOperation.SET, "key": "some_value", "value": "override"},
                {"mode": EnvOperation.PREPEND, "key": "some_list", "value": "start"},
            ),
            {"some_list": "path", "some_value": "3"},
            {"some_list": "start", "some_value": "override"},
        ),
    ],
)
def test_defaultenvpipeline_execute(handler_data, env_in, env_out):
    """
    Execute an DefaultEnvPipeline and check the resulting environment.
    """

    pipeline = DefaultEnvPipeline(handlers=handler_data, env_initial=env_in)
    new_env = pipeline.execute()

    assert new_env == {**env_out}
