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

from ifsbench import (Job, SrunLauncher, EnvHandler, EnvOperation,
    DefaultEnvPipeline, CpuBinding, CpuDistribution)

_test_env = DefaultEnvPipeline([
        EnvHandler(EnvOperation.SET, 'SOME_VALUE', '5'),
        EnvHandler(EnvOperation.SET, 'OTHER_VALUE', '6'),
        EnvHandler(EnvOperation.DELETE, 'SOME_VALUE'),
])

@pytest.mark.parametrize('cmd,job_in,library_paths,env_pipeline,custom_flags,env_out', [
    (['ls', '-l'], {'tasks': 64, 'cpus_per_task': 4}, [], None, [], {}),
    (['something'], {}, ['/library/path', '/more/paths'], None, [], {'LD_LIBRARY_PATH': '/library/path:/more/paths'}),
    (['whatever'], {'nodes': 12}, ['/library/path'], _test_env, [],
        {'LD_LIBRARY_PATH': '/library/path', 'OTHER_VALUE': '6'}),
])
def test_srunlauncher_prepare_env(tmp_path, cmd, job_in, library_paths, env_pipeline, custom_flags, env_out):
    """
    Test the env component of the LaunchData object that is returned by SrunLauncher.prepare.
    """
    launcher = SrunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(tmp_path, job, cmd, library_paths, env_pipeline, custom_flags)

    assert result.env == {**env_out}

@pytest.mark.parametrize('cmd,job_in,library_paths,env_pipeline,custom_flags', [
    (['ls', '-l'], {'tasks': 64, 'cpus_per_task': 4}, [], None, []),
    (['something'], {}, ['/library/path', '/more/paths'], None, []),
    (['whatever'], {'nodes': 12}, ['/library/path'], _test_env, []),
])
def test_srunlauncher_prepare_run_dir(tmp_path, cmd, job_in, library_paths, env_pipeline, custom_flags):
    """
    Test the run_dir component of the LaunchData object that is returned by SrunLauncher.prepare.
    """
    launcher = SrunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(tmp_path, job, cmd, library_paths, env_pipeline, custom_flags)

    assert result.run_dir == tmp_path

@pytest.mark.parametrize('cmd,job_in,library_paths,env_pipeline,custom_flags, cmd_out', [
    (['ls', '-l'], {'tasks': 64, 'cpus_per_task': 4}, [], None, [],
        ['srun', '--ntasks=64', '--cpus-per-task=4', 'ls', '-l']),
    (['something'], {}, ['/library/path', '/more/paths'], None, ['--some-more'],
        ['srun', '--some-more', 'something']),
    (['whatever'], {'nodes': 12, 'gpus_per_task': 2}, ['/library/path'], _test_env, [],
        ['srun', '--nodes=12', '--gpus-per-task=2', 'whatever']),
    (['bind_hell'], {'bind': CpuBinding.BIND_THREADS, 'distribute_local': CpuDistribution.DISTRIBUTE_CYCLIC},
        ['/library/path'], _test_env, [],
        ['srun', '--cpu-bind=threads', '--distribution=*:cyclic', 'bind_hell']),
])
def test_srunlauncher_prepare_cmd(tmp_path, cmd, job_in, library_paths, env_pipeline, custom_flags, cmd_out):
    """
    Test the cmd component of the LaunchData object that is returned by SrunLauncher.prepare.
    """
    launcher = SrunLauncher()
    job = Job(**job_in)

    result = launcher.prepare(tmp_path, job, cmd, library_paths, env_pipeline, custom_flags)

    # There is no fixed order of the srun flags, so we test for the sorted command array.
    assert sorted(cmd_out) == sorted(result.cmd)
