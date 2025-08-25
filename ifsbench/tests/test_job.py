# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Test :any:`Job` and its ability to derive job size
"""

import pytest

from ifsbench import Job, CpuConfiguration, CpuBinding, CpuDistribution


@pytest.mark.parametrize(
    'cpu_config',
    [
        {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
        {
            'sockets_per_node': 2,
            'cores_per_socket': 8,
            'threads_per_core': 2,
            'gpus_per_node': 4,
        },
        {
            'threads_per_core': 2,
            'gpus_per_node': 4,
        },
    ],
)
def test_cpuconfiguration_from_config_dump_config(cpu_config):

    cc = CpuConfiguration.from_config(cpu_config)

    conf_out = cc.dump_config()

    for field, field_value in CpuConfiguration.model_fields.items():
        if field not in cpu_config:
            value = conf_out.pop(field)
            # pylint: disable=unsubscriptable-object
            assert value == field_value.get_default()
            # pylint: enable=unsubscriptable-object
    assert conf_out == cpu_config


@pytest.mark.parametrize(
    'cpu_config,expected_cores_per_node',
    [
        ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2}, 16),
        (
            {
                'cores_per_socket': 8,
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            8,
        ),
        (
            {
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            1,
        ),
    ],
)
def test_cpuconfiguration_cores_per_node(cpu_config, expected_cores_per_node):

    cc = CpuConfiguration.from_config(cpu_config)

    cpn = cc.cores_per_node

    assert cpn == expected_cores_per_node


@pytest.mark.parametrize(
    'cpu_config,expected_threads_per_node',
    [
        ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2}, 32),
        (
            {
                'cores_per_socket': 8,
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            16,
        ),
        (
            {
                'gpus_per_node': 4,
            },
            1,
        ),
    ],
)
def test_cpuconfiguration_threads_per_node(cpu_config, expected_threads_per_node):

    cc = CpuConfiguration.from_config(cpu_config)

    tpn = cc.threads_per_node

    assert tpn == expected_threads_per_node


@pytest.mark.parametrize(
    'jobargs',
    [
        # Only specify number of tasks:
        {'tasks': 64},
        # Specify nodes and number of tasks per node:
        {'nodes': 4, 'tasks_per_node': 16},
        # Specify tasks and gpus_per_node.
        {'tasks': 64, 'gpus_per_node': 4},
    ],
)
def test_job_from_config_dump_config(jobargs):
    job = Job.from_config(jobargs)

    conf_out = job.dump_config()

    assert conf_out == jobargs


@pytest.mark.parametrize(
    'cpu_config,jobargs,jobattrs',
    [
        # Only specify number of tasks:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 64},
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per node:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'nodes': 4, 'tasks_per_node': 16},
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per socket:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'nodes': 4, 'tasks_per_socket': 8},
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': 8,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per socket with hyperthreading:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'nodes': 4, 'tasks_per_socket': 16, 'threads_per_core': 2},
            {
                'tasks': 128,
                'nodes': 4,
                'tasks_per_node': 32,
                'tasks_per_socket': 16,
                'cpus_per_task': None,
                'threads_per_core': 2,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Undersubscribe nodes:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'nodes': 4, 'tasks_per_socket': 2},
            {
                'tasks': 16,
                'nodes': 4,
                'tasks_per_node': 4,
                'tasks_per_socket': 2,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Fewer tasks than available:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 60, 'nodes': 4},
            {
                'tasks': 60,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify number of tasks that is less than total available in required nodes
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 60},
            {
                'tasks': 60,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Hybrid MPI+OpenMP
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 16, 'cpus_per_task': 4},
            {
                'tasks': 16,
                'nodes': 4,
                'tasks_per_node': 4,
                'tasks_per_socket': None,
                'cpus_per_task': 4,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Hybrid MPI+OpenMP+SMT
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 16, 'cpus_per_task': 8, 'threads_per_core': 2},
            {
                'tasks': 16,
                'nodes': 4,
                'tasks_per_node': 2,
                'tasks_per_socket': None,
                'cpus_per_task': 8,
                'threads_per_core': 2,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Hybrid MPI+OpenMP+SMT undersubscribed
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 14, 'cpus_per_task': 8, 'threads_per_core': 2},
            {
                'tasks': 14,
                'nodes': 4,
                'tasks_per_node': 2,
                'tasks_per_socket': None,
                'cpus_per_task': 8,
                'threads_per_core': 2,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Hybrid MPI+OpenMP+SMT with binding
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {
                'tasks': 16,
                'cpus_per_task': 8,
                'threads_per_core': 2,
                'bind': CpuBinding.BIND_CORES,
            },
            {
                'tasks': 16,
                'nodes': 4,
                'tasks_per_node': 2,
                'tasks_per_socket': None,
                'cpus_per_task': 8,
                'threads_per_core': 2,
                'bind': CpuBinding.BIND_CORES,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per node with remote distribution strategy:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {
                'nodes': 4,
                'tasks_per_node': 16,
                'distribute_remote': CpuDistribution.DISTRIBUTE_CYCLIC,
            },
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': CpuDistribution.DISTRIBUTE_CYCLIC,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per node with local distribution strategy:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {
                'nodes': 4,
                'tasks_per_node': 16,
                'distribute_local': CpuDistribution.DISTRIBUTE_BLOCK,
            },
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': CpuDistribution.DISTRIBUTE_BLOCK,
            },
        ),
        # Only specify number of tasks and use GPUs:
        (
            {
                'sockets_per_node': 2,
                'cores_per_socket': 8,
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            {'tasks': 64, 'gpus_per_node': 2},
            {
                'tasks': 64,
                'nodes': 16,
                'tasks_per_node': 4,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'gpus_per_node': 2,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Only specify number of tasks and tasks_per_node and use GPUs:
        (
            {
                'sockets_per_node': 2,
                'cores_per_socket': 8,
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            {'tasks': 64, 'tasks_per_node': 4, 'gpus_per_node': 2},
            {
                'tasks': 64,
                'nodes': 16,
                'tasks_per_node': 4,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'gpus_per_node': 2,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Only specify number of tasks and tasks_per_node and use GPUs:
        (
            {
                'sockets_per_node': 2,
                'cores_per_socket': 8,
                'threads_per_core': 2,
                'gpus_per_node': 4,
            },
            {'tasks': 64, 'tasks_per_node': 2, 'gpus_per_node': 1},
            {
                'tasks': 64,
                'nodes': 32,
                'tasks_per_node': 2,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'gpus_per_node': 1,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Mismatch between gpus_per_node and available GPUs.
        (
            {
                'sockets_per_node': 2,
                'cores_per_socket': 56,
                'threads_per_core': 2,
                'gpus_per_node': 8,
            },
            {'tasks': 64, 'gpus_per_node': 16},
            None,
        ),
    ],
)
def test_job_calculate_missing(cpu_config, jobargs, jobattrs):
    """
    Test various configuration specifications and fill-in for derived values.
    If jobattrs is empty, creating the job is assumed to fail with a ValueError.
    """

    cpu_config = CpuConfiguration(
        sockets_per_node=cpu_config['sockets_per_node'],
        cores_per_socket=cpu_config['cores_per_socket'],
        threads_per_core=cpu_config['threads_per_core'],
        gpus_per_node=cpu_config.pop('gpus_per_node', 0),
    )

    job = Job(**jobargs)

    if jobattrs:
        job.calculate_missing(cpu_config)
    else:
        with pytest.raises(ValueError):
            job.calculate_missing(cpu_config)
        return

    for attr, value in jobattrs.items():
        assert getattr(job, attr) == value


@pytest.mark.parametrize(
    'cpu_config,jobargs,jobattrs',
    [
        # Clone after applying CpuConfiguration
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'tasks': 64},
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Specify nodes and number of tasks per node:
        (
            {'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
            {'nodes': 4, 'tasks_per_node': 16},
            {
                'tasks': 64,
                'nodes': 4,
                'tasks_per_node': 16,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
        # Clone without applying any config
        (
            None,
            {'tasks': 64, 'tasks_per_node': 2, 'gpus_per_node': 3},
            {
                'tasks': 64,
                'nodes': None,
                'tasks_per_node': 2,
                'tasks_per_socket': None,
                'cpus_per_task': None,
                'gpus_per_node': 3,
                'threads_per_core': None,
                'bind': None,
                'distribute_remote': None,
                'distribute_local': None,
            },
        ),
    ],
)
def test_job_clone(cpu_config, jobargs, jobattrs):

    job = Job(**jobargs)

    if cpu_config:
        cpu_conf = CpuConfiguration(
            sockets_per_node=cpu_config['sockets_per_node'],
            cores_per_socket=cpu_config['cores_per_socket'],
            threads_per_core=cpu_config['threads_per_core'],
            gpus_per_node=cpu_config.pop('gpus_per_node', 0),
        )
        job.calculate_missing(cpu_conf)

    cloned_job = job.clone()

    for attr, value in jobattrs.items():
        assert getattr(cloned_job, attr) == value

    job.distribute_remote = 'user'

    assert cloned_job.distribute_remote is None
