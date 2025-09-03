# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the :class:`DefaultArch` implementation.
"""

import pytest

from ifsbench import DefaultArch, CpuConfiguration, EnvHandler, EnvOperation, Job, MpirunLauncher, SrunLauncher

_cpu_config_1 = CpuConfiguration(
    sockets_per_node = 2,
    cores_per_socket = 64,
    threads_per_core = 2,
    gpus_per_node = 0
)


_cpu_config_2 = CpuConfiguration(
    sockets_per_node = 2,
    cores_per_socket = 56,
    threads_per_core = 2,
    gpus_per_node = 8
)


@pytest.mark.parametrize('arch_in, job_in, job_out, launcher_out', [
    (
        {'launcher': {'class_name': 'SrunLauncher'}, 'cpu_config': _cpu_config_1, 'set_explicit': False},
        {'tasks': 64, 'cpus_per_task': 4, 'threads_per_core': 1},
        {'tasks': 64, 'cpus_per_task': 4, 'threads_per_core': 1},
        SrunLauncher()
    ),
    (
        {'launcher': MpirunLauncher(), 'cpu_config': _cpu_config_1, 'set_explicit': True},
        {'tasks': 64, 'cpus_per_task': 4, 'threads_per_core': 1},
        {'tasks': 64, 'cpus_per_task': 4, 'threads_per_core': 1, 'nodes': 2, 'tasks_per_node': 32},
        MpirunLauncher()
    ),
    (
        {'launcher': SrunLauncher(), 'cpu_config': _cpu_config_2, 'set_explicit': False,
         'env_handler': [EnvHandler(mode=EnvOperation.DELETE, key='SOME_ENV')]},
        {'tasks': 1},
        {'tasks': 1},
        SrunLauncher()
    ),
    (
        {'launcher': MpirunLauncher(), 'cpu_config': _cpu_config_2, 'set_explicit': True},
        {'tasks': 64, 'gpus_per_node': 16},
        None,
        None
    ),
    (
        {'launcher': MpirunLauncher(), 'cpu_config': _cpu_config_2, 'set_explicit': True,
         'launcher_flags': ['--account=myaccount']},
        {'tasks': 64, 'gpus_per_node': 32},
        None,
        None
    )])
def test_defaultarch_process(arch_in, job_in, job_out, launcher_out):
    """
    Test the :meth:`DefaultArch.process_job` implementation by checking that
    the resulting Job and Launcher objects are correct.
    """
    arch = DefaultArch(**arch_in)
    job = Job(**job_in)

    if job_out is None:
        with pytest.raises(ValueError):
            result = arch.process_job(job)
        return

    result = arch.process_job(job)

    # DefaultArch shouldn't add any handlers or default flags.
    assert result.env_handlers == arch_in.get('env_handlers', [])
    assert result.default_launcher_flags == arch_in.get('launcher_flags', [])

    # Check that the right launcher is returned. Check only the type here,
    # as the launchers dont implement __eq__ by default.
    # pylint: disable=C0123
    assert type(result.default_launcher) == type(launcher_out)

    # Check that the resulting job is what we expect.
    for key, value in job_out.items():
        assert value == getattr(result.job, key)
