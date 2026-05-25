# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the  :class:`CommandWrapLauncher` implementation.
"""

import pytest

from ifsbench import (
    Job,
    CommandWrapLauncher,
    DirectLauncher,
    SrunLauncher,
    EnvHandler,
    EnvOperation,
    DefaultEnvPipeline,
)


@pytest.fixture(name='test_env')
def fixture_test_env():
    return DefaultEnvPipeline(
        handlers=[
            EnvHandler(mode=EnvOperation.SET, key='SOME_VALUE', value='5'),
            EnvHandler(mode=EnvOperation.SET, key='OTHER_VALUE', value='6'),
            EnvHandler(mode=EnvOperation.DELETE, key='SOME_VALUE'),
        ]
    )


@pytest.fixture(name='test_env_none')
def fixture_test_env_none():
    return None


@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [[], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
@pytest.mark.parametrize('prepend_flags', [[], ['valgrind', '--tool=helgrind']])
@pytest.mark.parametrize('append_flags', [[], ['--p=5']])
def test_commandwraplauncher_run_dir(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    prepend_flags,
    append_flags,
    request,
):
    """
    Test the run_dir component of the LaunchData object that is returned by
    CommandWrapLauncher.wrap.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = CommandWrapLauncher(
        flags=custom_flags, prepend_flags=prepend_flags, append_flags=append_flags
    )
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    assert result.run_dir == base_launch_data.run_dir


@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [[], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
@pytest.mark.parametrize('prepend_flags', [[], ['valgrind', '--tool=helgrind']])
@pytest.mark.parametrize('append_flags', [[], ['--p=5']])
def test_commandwraplauncher_env(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    prepend_flags,
    append_flags,
    request,
):
    """
    Test the env component of the LaunchData object that is returned by
    CommandWrapLauncher.wrap.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = CommandWrapLauncher(
        flags=custom_flags, prepend_flags=prepend_flags, append_flags=append_flags
    )
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    assert result.env == base_launch_data.env


@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [None, [], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
@pytest.mark.parametrize('prepend_flags', [[], ['valgrind', '--tool=helgrind']])
@pytest.mark.parametrize('append_flags', [[], ['--p=5']])
def test_commandwraplauncher_cmd(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    prepend_flags,
    append_flags,
    request,
):
    """
    Test the cmd component of the LaunchData object that is returned by
    CommandWrapLauncher.wrap.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    if custom_flags is None:
        launcher = CommandWrapLauncher(prepend_flags=prepend_flags, append_flags=append_flags)
    else:
        launcher = CommandWrapLauncher(
            flags=custom_flags, prepend_flags=prepend_flags, append_flags=append_flags
        )
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    if not custom_flags:
        assert prepend_flags + base_launch_data.cmd + append_flags == result.cmd
    else:
        assert prepend_flags + base_launch_data.cmd + custom_flags + append_flags == result.cmd
