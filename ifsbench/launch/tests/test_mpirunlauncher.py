# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Arch` implementations
"""

import pytest

from ifsbench import (
    Job,
    MpirunLauncher,
    EnvHandler,
    EnvOperation,
    DefaultEnvPipeline,
    CpuBinding,
    CpuDistribution,
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


@pytest.mark.parametrize(
    'cmd,job_in,library_paths,env_pipeline_name,custom_flags,env_out',
    [
        (['ls', '-l'], {'tasks': 64, 'cpus_per_task': 4}, [], 'test_env_none', [], {}),
        (
            ['something'],
            {},
            ['/library/path', '/more/paths'],
            'test_env_none',
            [],
            {'LD_LIBRARY_PATH': '/library/path:/more/paths'},
        ),
        (
            ['whatever'],
            {'nodes': 12},
            ['/library/path'],
            'test_env',
            [],
            {'LD_LIBRARY_PATH': '/library/path', 'OTHER_VALUE': '6'},
        ),
    ],
)
def test_mpirunLauncher_prepare_env(
    tmp_path,
    cmd,
    job_in,
    library_paths,
    env_pipeline_name,
    custom_flags,
    env_out,
    request,
):
    """
    Test the env component of the LaunchData object that is returned by MpirunLauncher.prepare.
    """
    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = MpirunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(
        tmp_path, job, cmd, library_paths, env_pipeline, custom_flags
    )

    assert result.env == {**env_out}


@pytest.mark.parametrize(
    'cmd,job_in,library_paths,env_pipeline_name,custom_flags',
    [
        (['ls', '-l'], {'tasks': 64, 'cpus_per_task': 4}, [], 'test_env_none', []),
        (['something'], {}, ['/library/path', '/more/paths'], 'test_env_none', []),
        (['whatever'], {'nodes': 12}, ['/library/path'], 'test_env', []),
    ],
)
def test_mpirunLauncher_prepare_run_dir(
    tmp_path, cmd, job_in, library_paths, env_pipeline_name, custom_flags, request
):
    """
    Test the run_dir component of the LaunchData object that is returned by MpirunLauncher.prepare.
    """
    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = MpirunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(
        tmp_path, job, cmd, library_paths, env_pipeline, custom_flags
    )

    assert result.run_dir == tmp_path


@pytest.mark.parametrize(
    'cmd,job_in,library_paths,env_pipeline_name,custom_flags, cmd_out',
    [
        (
            ['ls', '-l'],
            {'tasks': 64, 'cpus_per_task': 4},
            [],
            'test_env_none',
            [],
            ['mpirun', '-np 64', '-cpus-per-proc 4', 'ls', '-l'],
        ),
        (
            ['something'],
            {},
            ['/library/path', '/more/paths'],
            'test_env_none',
            ['--some-more'],
            ['mpirun', '--some-more', 'something'],
        ),
        (
            ['whatever'],
            {'nodes': 12, 'gpus_per_task': 2},
            ['/library/path'],
            'test_env',
            [],
            ['mpirun', 'whatever'],
        ),
        (
            ['bind_hell'],
            {
                'bind': CpuBinding.BIND_THREADS,
                'distribute_local': CpuDistribution.DISTRIBUTE_CYCLIC,
            },
            ['/library/path'],
            'test_env',
            [],
            ['mpirun', '--bind-to', 'hwthread', '--map-by', 'numa', 'bind_hell'],
        ),
    ],
)
def test_mpirunLauncher_prepare_cmd(
    tmp_path,
    cmd,
    job_in,
    library_paths,
    env_pipeline_name,
    custom_flags,
    cmd_out,
    request,
):
    """
    Test the cmd component of the LaunchData object that is returned by MpirunLauncher.prepare.
    """
    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = MpirunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(
        tmp_path, job, cmd, library_paths, env_pipeline, custom_flags
    )

    # There is no fixed order of the srun flags, so we test for the sorted command array.
    assert sorted(cmd_out) == sorted(result.cmd)
