# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from ifsbench.env import DefaultEnvPipeline, EnvOperation, EnvHandler
from ifsbench.job import CpuBinding, CpuDistribution
from ifsbench.logging import warning
from ifsbench.launcher.launcher import Launcher, LaunchData

class MpirunLauncher(Launcher):
    """
    :any:`Launcher` implementation for a standard mpirun
    """
    job_options_map = {
        'tasks': '--n={}',
        'tasks_per_node': '--npernode={}',
        'tasks_per_socket': '--npersocket={}',
        'cpus_per_task': '--cpus-per-proc={}',
    }

    bind_options_map = {
        CpuBinding.BIND_NONE: ['--bind-to', 'none'],
        CpuBinding.BIND_SOCKETS: ['--bind-to', 'socket'],
        CpuBinding.BIND_CORES: ['--bind-to', 'core'],
        CpuBinding.BIND_THREADS: ['--bind-to', 'hwthread'],
        CpuBinding.BIND_USER: [],
    }

    distribution_options_map = {
        CpuDistribution.DISTRIBUTE_BLOCK: 'core',
        CpuDistribution.DISTRIBUTE_CYCLIC: 'numa',
    }

    def _get_distribution_options(self, job):
        """Return options for task distribution"""
        do_nothing = [CpuDistribution.DISTRIBUTE_DEFAULT, CpuDistribution.DISTRIBUTE_USER]
        if hasattr(job, 'distribute_remote') and job.distribute_remote not in do_nothing:
            warning('Specified remote distribution option ignored in MpirunLauncher')

        if job.distribute_local is None or job.distribute_local in do_nothing:
            return []

        return ['--map-by', f'{self.distribution_options_map[job.distribute_local]}']

    def prepare(self, run_dir, job, cmd, library_paths=None, env_pipeline=None, custom_flags=None):
        executable = 'mpirun'
        if env_pipeline is None:
            env_pipeline = DefaultEnvPipeline()

        flags = []

        for attr, option in self.job_options_map.items():
            value = getattr(job, attr, None)

            if value is not None:
                flags += [option.format(value)]

        if job.bind:
            flags += list(self.bind_options_map[job.bind])

        flags += self._get_distribution_options(job)

        if custom_flags:
            flags += custom_flags

        if library_paths:
            for path in library_paths:
                env_pipeline.add(EnvHandler(EnvOperation.APPEND, 'LD_LIBRARY_PATH', str(path)))

        flags += cmd

        env = env_pipeline.execute()

        return LaunchData(
            run_dir=run_dir,
            cmd=[executable] + flags,
            env=env
        )
