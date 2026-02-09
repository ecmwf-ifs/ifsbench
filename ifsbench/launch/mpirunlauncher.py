# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import List, Optional

from ifsbench.env import DefaultEnvPipeline, EnvOperation, EnvPipeline, EnvHandler
from ifsbench.job import CpuBinding, CpuDistribution, Job
from ifsbench.logging import warning
from ifsbench.launch.launcher import Launcher, LaunchData


class MpirunLauncher(Launcher):
    """
    :any:`Launcher` implementation for a standard mpirun
    """

    _job_options_map = {
        "tasks": "-n {}",
        "tasks_per_node": "--npernode {}",
        "tasks_per_socket": "--npersocket {}",
    }

    _bind_options_map = {
        CpuBinding.BIND_NONE: ["--bind-to", "none"],
        CpuBinding.BIND_SOCKETS: ["--bind-to", "socket"],
        CpuBinding.BIND_CORES: ["--bind-to", "core"],
        CpuBinding.BIND_THREADS: ["--bind-to", "hwthread"],
        CpuBinding.BIND_USER: [],
    }

    _distribution_options_map = {
        CpuDistribution.DISTRIBUTE_BLOCK: "core",
        CpuDistribution.DISTRIBUTE_CYCLIC: "numa",
    }

    def _get_distribution_options(self, job: Job) -> List[str]:
        """Return options for task distribution"""
        do_nothing = [
            CpuDistribution.DISTRIBUTE_DEFAULT,
            CpuDistribution.DISTRIBUTE_USER,
            None,
        ]
        if (
            hasattr(job, "distribute_remote")
            and job.distribute_remote not in do_nothing
        ):
            warning("Specified remote distribution option ignored in MpirunLauncher")

        # By default use core mapping. At least that's the default in the
        # OpenMPI implementation
        # (https://docs.open-mpi.org/en/main/man-openmpi/man1/mpirun.1.html#label-schizo-ompi-map-by).
        map_by = "core"

        if job.distribute_local and job.distribute_local not in do_nothing:
            map_by = self._distribution_options_map[job.distribute_local]
        elif job.cpus_per_task is None:
            # If no local distribution must be set and the number of threads
            # isn't specified, we don't have to add any flags.
            return []

        # If multithreading is used, we have to specify the number of threads
        # per process in the map_by statement.
        if job.cpus_per_task:
            return ["--map-by", f"{map_by}:PE={job.cpus_per_task}"]

        return ["--map-by", f"{map_by}"]

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:
        executable = "mpirun"
        if env_pipeline is None:
            env_pipeline = DefaultEnvPipeline()
        else:
            env_pipeline = env_pipeline.copy(deep=True)

        flags = list(self.flags)

        for attr, option in self._job_options_map.items():
            value = getattr(job, attr, None)

            if value is not None:
                # Split the resulting split up if it contains spaces. Otherwise
                # we might end up with a command like ['mpirun', '-n 4', 'program']
                # which causes errors. We want ['mpirun', '-n', '4', 'program'].
                flags += option.format(value).split(" ")

        if job.bind:
            flags += list(self._bind_options_map[job.bind])

        flags += self._get_distribution_options(job)

        if custom_flags:
            flags += custom_flags

        if library_paths:
            for path in library_paths:
                env_pipeline.add(
                    EnvHandler(
                        mode=EnvOperation.APPEND, key="LD_LIBRARY_PATH", value=str(path)
                    )
                )

        if job.cpus_per_task:
            # We automatically set OMP_NUM_THREADS here. This may not be
            # necessary for each application (as not all application may use
            # OpenMP-based multithreading.
            env_pipeline.add(
                EnvHandler(
                    mode=EnvOperation.APPEND,
                    key="OMP_NUM_THREADS",
                    value=str(job.cpus_per_task),
                )
            )

        flags += cmd

        env = env_pipeline.execute()

        return LaunchData(run_dir=run_dir, cmd=[executable] + flags, env=env)
