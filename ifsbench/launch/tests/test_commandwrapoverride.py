# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the :class:`CommandWrapOverride` implementation.
"""

import pytest

from ifsbench import CommandWrapOverride


@pytest.mark.parametrize(
    'prepend_cmd,cmd,append_cmd,expected',
    [
        ([], ['my_exec', '--flag'], [], ['my_exec', '--flag']),
        (['valgrind'], ['my_exec'], [], ['valgrind', 'my_exec']),
        ([], ['my_exec'], ['--postflag'], ['my_exec', '--postflag']),
        (
            ['valgrind', '--tool=helgrind'],
            ['my_exec', '--flag'],
            ['--p=5'],
            ['valgrind', '--tool=helgrind', 'my_exec', '--flag', '--p=5'],
        ),
    ],
)
def test_commandwrapoverride_override(prepend_cmd, cmd, append_cmd, expected):
    """Test that CommandWrapOverride.override builds the expected command."""
    override = CommandWrapOverride(prepend_cmd=prepend_cmd, append_cmd=append_cmd)
    assert override.override(cmd) == expected


def test_commandwrapoverride_from_config():
    """Test serialisation round-trip for CommandWrapOverride."""
    override = CommandWrapOverride(
        prepend_cmd=['valgrind', '--tool=helgrind'],
        append_cmd=['--p=5'],
    )
    config = override.dump_config()
    restored = CommandWrapOverride.from_config(config)
    assert restored == override
