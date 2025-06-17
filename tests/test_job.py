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


@pytest.mark.parametrize('cpu_config,jobargs,jobattrs', [
    # Only specify number of tasks:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 64},
     {'tasks': 64, 'get_tasks': 64, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Specify nodes and number of tasks per node:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_node': 16},
     {'tasks': None, 'get_tasks': 64, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': 16, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Specify nodes and number of tasks per socket:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 8},
     {'tasks': None, 'get_tasks': 64, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 16, 'tasks_per_socket': 8,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Specify nodes and number of tasks per socket with hyperthreading:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 16, 'threads_per_core': 2},
     {'tasks': None, 'get_tasks': 128, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 32, 'tasks_per_socket': 16,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': 2, 'get_threads_per_core': 2,
      'get_threads': 128, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Undersubscribe nodes:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 2},
     {'tasks': None, 'get_tasks': 16, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 4, 'tasks_per_socket': 2,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 16, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Less tasks than available:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 60, 'nodes': 4},
     {'tasks': 60, 'get_tasks': 60, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 60, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Specify number of tasks that is less than total available in required nodes
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 60},
     {'tasks': 60, 'get_tasks': 60, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 60, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Hybrid MPI+OpenMP
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 4},
     {'tasks': 16, 'get_tasks': 16, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 4, 'tasks_per_socket': None,
      'cpus_per_task': 4, 'get_cpus_per_task': 4,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Hybrid MPI+OpenMP+SMT
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 8, 'threads_per_core': 2},
     {'tasks': 16, 'get_tasks': 16, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 2, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'get_cpus_per_task': 8,
      'threads_per_core': 2, 'get_threads_per_core': 2,
      'get_threads': 128, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Hybrid MPI+OpenMP+SMT undersubscribed
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 14, 'cpus_per_task': 8, 'threads_per_core': 2},
     {'tasks': 14, 'get_tasks': 14, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 2, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'get_cpus_per_task': 8,
      'threads_per_core': 2, 'get_threads_per_core': 2,
      'get_threads': 112, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Hybrid MPI+OpenMP+SMT with binding
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 8, 'threads_per_core': 2, 'bind': CpuBinding.BIND_CORES},
     {'tasks': 16, 'get_tasks': 16, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 2, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'get_cpus_per_task': 8,
      'threads_per_core': 2, 'get_threads_per_core': 2,
      'get_threads': 128, 'bind': CpuBinding.BIND_CORES,
      'distribute_remote': None, 'distribute_local': None}),
    # Specify nodes and number of tasks per node with remote distribution strategy:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_node': 16, 'distribute_remote': CpuDistribution.DISTRIBUTE_CYCLIC},
     {'tasks': None, 'get_tasks': 64, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': 16, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None,
      'distribute_remote': CpuDistribution.DISTRIBUTE_CYCLIC, 'distribute_local': None}),
    # Specify nodes and number of tasks per node with local distribution strategy:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_node': 16, 'distribute_local': CpuDistribution.DISTRIBUTE_BLOCK},
     {'tasks': None, 'get_tasks': 64, 'nodes': 4, 'get_nodes': 4,
      'tasks_per_node': 16, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None,
      'distribute_remote': None, 'distribute_local': CpuDistribution.DISTRIBUTE_BLOCK}),
    # Only specify number of tasks and use GPUs:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2, 'gpus_per_node': 4},
     {'tasks': 64, 'gpus_per_node': 4},
     {'tasks': 64, 'get_tasks': 64, 'nodes': None, 'get_nodes': 4,
      'tasks_per_node': None, 'get_tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'gpus_per_node': 4, 'get_gpus_per_node': 4,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Only specify number of tasks and tasks_per_node and use GPUs:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2, 'gpus_per_node': 4},
     {'tasks': 64, 'tasks_per_node': 4, 'gpus_per_node': 4},
     {'tasks': 64, 'get_tasks': 64, 'nodes': None, 'get_nodes': 16,
      'tasks_per_node': 4, 'get_tasks_per_node': 4, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'gpus_per_node': 4, 'get_gpus_per_node': 4,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
    # Only specify number of tasks and tasks_per_node and an incomatible
    # number of GPUs:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2, 'gpus_per_node': 4},
     {'tasks': 64, 'tasks_per_node': 4, 'gpus_per_node': 16},
     {}),
    # Only specify number of tasks and tasks_per_node and use GPUs:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2, 'gpus_per_node': 4},
     {'tasks': 64, 'tasks_per_node': 2, 'gpus_per_node': 2},
     {'tasks': 64, 'get_tasks': 64, 'nodes': None, 'get_nodes': 32,
      'tasks_per_node': 2, 'get_tasks_per_node': 2, 'tasks_per_socket': None,
      'cpus_per_task': None, 'get_cpus_per_task': 1,
      'gpus_per_node': 2, 'get_gpus_per_node': 2,
      'threads_per_core': None, 'get_threads_per_core': 1,
      'get_threads': 64, 'bind': None, 'distribute_remote': None, 'distribute_local': None}),
])
def test_job(cpu_config, jobargs, jobattrs):
    """
    Test various configuration specifications and fill-in for derived values.
    If jobattrs is empty, creating the job is assumed to fail with a ValueError.
    """

    class MyCpuConfig(CpuConfiguration):
        """Dummy cpu configuration"""
        sockets_per_node = cpu_config['sockets_per_node']
        cores_per_socket = cpu_config['cores_per_socket']
        threads_per_core = cpu_config['threads_per_core']
        gpus_per_node = cpu_config.pop('gpus_per_node', 0)

    if jobattrs:
        job = Job(MyCpuConfig, **jobargs)
    else:
        with pytest.raises(ValueError):
            job = Job(MyCpuConfig, **jobargs)

    for attr, value in jobattrs.items():
        if value is None:
            with pytest.raises(AttributeError):
                if attr.startswith('get_'):
                    _ = getattr(job, attr)()
                else:
                    _ = getattr(job, attr)
        else:
            if attr.startswith('get_'):
                assert getattr(job, attr)() == value
            else:
                assert getattr(job, attr) == value
