# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for the LaunchData class.
"""

import sys

import pytest

from ifsbench.launch import LaunchData


@pytest.fixture(name='python_exec')
def fixture_python():
    """
    Return the currently used Python executable.
    """
    return sys.executable


@pytest.mark.parametrize(
    'flags, env, files',
    [
        (
            ['-c', "from pathlib import Path; Path('test.txt').touch()"],
            {},
            ['test.txt'],
        ),
        (
            [
                '-c',
                "import os; from pathlib import Path; Path(os.environ['TARGET_FILE']).touch()",
            ],
            {'TARGET_FILE': 'env_file.txt'},
            ['env_file.txt'],
        ),
    ],
)
def test_launchdata_launch_python(tmp_path, python_exec, flags, env, files):
    """
    Test the LaunchData.launch method.

    To do this, we launch an external Python executable which creates files,
    based on the given flags and environment variables. Afterwards we check the
    existence of these files.
    """
    launch_data = LaunchData(run_dir=tmp_path, env=env, cmd=[python_exec] + flags)

    launch_data.launch()

    for file in files:
        assert (tmp_path / file).exists()
