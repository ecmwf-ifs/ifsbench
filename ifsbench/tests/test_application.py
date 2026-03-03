# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Application` implementations.
"""

from pathlib import Path

import pytest

from ifsbench import DefaultApplication, Job, EnvHandler, EnvOperation


@pytest.mark.parametrize(
    'job, command, data_handlers, env_handlers, library_paths',
    [
        (Job(tasks=5), ['ls', '-l'], None, None, None),
        (Job(nodes=12), ['ls', '-l'], [], [], []),
        (
            Job(nodes=12),
            ['ls', '-l'],
            [
                {
                    'class_name': 'ExtractHandler',
                    'archive_path': 'in',
                    'target_dir': 'out',
                }
            ],
            [],
            [Path('/some/path')],
        ),
        (Job(nodes=12), ['ls', '-l'], [], [EnvHandler(mode=EnvOperation.CLEAR)], []),
    ],
)
def test_default_application(tmp_path, job, command, data_handlers, env_handlers, library_paths):
    config = {'command': command}
    if data_handlers is not None:
        config['data_handlers'] = data_handlers
    if env_handlers is not None:
        config['env_handlers'] = env_handlers
    if library_paths is not None:
        config['library_paths'] = library_paths
    application = DefaultApplication.from_config(config=config)

    assert application.get_command(tmp_path, job) == command

    if library_paths:
        assert application.get_library_paths(tmp_path, job) == library_paths
    else:
        assert len(application.get_library_paths(tmp_path, job)) == 0

    if env_handlers:
        env_out = application.get_env_handlers(tmp_path, job)
        assert len(env_out) == len(env_handlers)
        assert [type(x) for x in env_out] == [type(x) for x in env_handlers]
    else:
        assert len(application.get_env_handlers(tmp_path, job)) == 0

    if data_handlers:
        data_out = application.get_data_handlers(tmp_path, job)
        assert len(data_out) == len(data_handlers)
        assert [type(x).__name__ for x in data_out] == [dh['class_name'] for dh in data_handlers]
    else:
        assert len(application.get_data_handlers(tmp_path, job)) == 0
