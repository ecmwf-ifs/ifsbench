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

from ifsbench.env import (
    EnvHandler, EnvOperation, DefaultEnvPipeline
)

@pytest.mark.parametrize('mode,key,value,success', [
    (EnvOperation.SET, 'some_key', 'some_value', True),
    (EnvOperation.SET, None, 'some_value', False),
    (EnvOperation.SET, 'some_key', None, True),
    (EnvOperation.SET, None, None, False),
    (EnvOperation.DELETE, 'some_key', 'some_value', True),
    (EnvOperation.DELETE, None, 'some_value', False),
    (EnvOperation.DELETE, 'some_key', None, True),
    (EnvOperation.DELETE, None, None, False),
    (EnvOperation.APPEND, 'some_key', 'some_value', True),
    (EnvOperation.APPEND, None, 'some_value', False),
    (EnvOperation.APPEND, 'some_key', None, False),
    (EnvOperation.APPEND, None, None, False),
    (EnvOperation.PREPEND, 'some_key', 'some_value', True),
    (EnvOperation.PREPEND, None, 'some_value', False),
    (EnvOperation.PREPEND, 'some_key', None, False),
    (EnvOperation.PREPEND, None, None, False),
    (EnvOperation.CLEAR, 'some_key', 'some_value', True),
    (EnvOperation.CLEAR, None, 'some_value', True),
    (EnvOperation.CLEAR, 'some_key', None, True),
    (EnvOperation.CLEAR, None, None, True),
])
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
        EnvHandler(mode, key, value)

@pytest.mark.parametrize('mode,key,value,env_in,env_out', [
    (EnvOperation.SET, 'some_key', 'some_value', {}, {'some_key': 'some_value'}),
    (EnvOperation.SET, 'some_key', 'new_value', {'some_key': 'some_value'}, {'some_key': 'new_value'}),
    (EnvOperation.SET, 'some_key', None, {'some_key': 'some_value'}, {'some_key': None}),
    (EnvOperation.DELETE, 'some_key', None, {}, {}),
    (EnvOperation.DELETE, 'some_key', 'new_value', {'some_key': 'some_value'}, {}),
    (EnvOperation.CLEAR, 'some_key', None, {}, {}),
    (EnvOperation.CLEAR, None, None, {'some_key': 'some_value', 'other_key': None}, {}),
    (EnvOperation.APPEND, 'some_list', 'some_value', {}, {'some_list': 'some_value'}),
    (EnvOperation.APPEND, 'some_list', 'new_value', {'some_list': 'some_value'},
        {'some_list': 'some_value'+os.pathsep+'new_value'}),
    (EnvOperation.PREPEND, 'some_list', 'some_value', {}, {'some_list': 'some_value'}),
    (EnvOperation.PREPEND, 'some_list', 'some_value', {'some_list': None}, {'some_list': 'some_value'}),
    (EnvOperation.PREPEND, 'some_list', 'new_value', {'some_list': 'some_value'},
        {'some_list': 'new_value'+os.pathsep+'some_value'}),
])
def test_envhandler_execute(mode, key, value, env_in, env_out):
    """
    Execute an EnvHandler and make sure that the output is correct.
    """
    handler = EnvHandler(mode, key, value)
    env = {**env_in}

    handler.execute(env)

    assert env == {**env_out}


@pytest.mark.parametrize('handler_data, env_in, env_out', [
    ((), {}, {}),
    ((), {'some_value': None, 'other_value': '2'}, {'some_value': None, 'other_value': '2'}),
    (
        ((EnvOperation.SET, 'some_value'), (EnvOperation.CLEAR,), (EnvOperation.SET, 'other_value', '3')),
        {}, {'other_value': '3'}
    ),
    (
        ((EnvOperation.APPEND, 'some_list', 'end'), (EnvOperation.APPEND, 'some_list', 'endend'),
         (EnvOperation.PREPEND, 'some_list', 'start')),
        {'some_list': 'path'}, {'some_list': 'start'+os.pathsep+'path'+os.pathsep+'end'+os.pathsep+'endend'}
    ),
    (
        ((EnvOperation.DELETE, 'some_list'), (EnvOperation.APPEND, 'some_list', 'endend'),
         (EnvOperation.PREPEND, 'some_list', 'start')),
        {'some_list': 'path'}, {'some_list': 'start'+os.pathsep+'endend'}
    ),
    (
        ((EnvOperation.PREPEND, 'some_list', 'start'), (EnvOperation.SET, 'some_list', 'override'),
         (EnvOperation.PREPEND, 'some_list', 'start')),
        {'some_list': 'path'}, {'some_list': 'start'+os.pathsep+'override'}
    ),
    (
        ((EnvOperation.DELETE, 'some_list'), (EnvOperation.SET, 'some_value', 'override'),
         (EnvOperation.PREPEND, 'some_list', 'start')),
        {'some_list': 'path', 'some_value': '3'}, {'some_list': 'start' , 'some_value': 'override'}
    ),
])
def test_defaultenvpipeline_execute(handler_data, env_in, env_out):
    """
    Execute an DefaultEnvPipeline and check the resulting environment.
    """
    handlers = []
    for data in handler_data:
        handlers.append(EnvHandler(*data))

    pipeline = DefaultEnvPipeline(handlers, env_in)
    new_env = pipeline.execute()

    assert new_env == {**env_out}
