# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Application` implementations.
"""

import pytest

from ifsbench import DefaultApplication, Job, EnvHandler, EnvOperation
from ifsbench.data import ExtractHandler

@pytest.mark.parametrize('job, command, data_handlers, env_handlers, library_paths', [
    (Job(tasks=5), ['ls', '-l'], None, None, None),
    (Job(nodes=12), ['ls', '-l'], [], [], []),
    (Job(nodes=12), ['ls', '-l'], [ExtractHandler(archive_path='in', target_dir='out')], [], ['/some/path']),
    (Job(nodes=12), ['ls', '-l'], [], [EnvHandler(EnvOperation.CLEAR)], []),
])
def test_default_application(tmp_path, job, command, data_handlers, env_handlers, library_paths):
    application = DefaultApplication(command, data_handlers, env_handlers, library_paths)

    assert application.get_command(tmp_path, job) == command

    if library_paths:
        assert application.get_library_paths(tmp_path, job) == library_paths
    else:
        assert application.get_library_paths(tmp_path, job) == []


    if env_handlers:
        env_out = application.get_env_handlers(tmp_path, job)
        assert len(env_out) == len(env_handlers)
        assert [type(x) for x in env_out] == [type(x) for x in env_handlers]
    else:
        assert application.get_env_handlers(tmp_path, job) == []


    if data_handlers:
        data_out = application.get_data_handlers(tmp_path, job)
        assert len(data_out) == len(data_handlers)
        assert [type(x) for x in data_out] == [type(x) for x in data_handlers]
    else:
        assert application.get_data_handlers(tmp_path, job) == []
