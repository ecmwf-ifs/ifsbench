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
from ifsbench.logging import debug
from ifsbench.launch.launcher import Launcher, LaunchData


class SrunLauncher(Launcher):
    """
    :any:`Launcher` implementation for Slurm's srun.
    """

    _job_options_map = {
        "nodes": "--nodes={}",
        "tasks": "--ntasks={}",
        "tasks_per_node": "--ntasks-per-node={}",
        "tasks_per_socket": "--ntasks-per-socket={}",
        "cpus_per_task": "--cpus-per-task={}",
        "threads_per_core": "--ntasks-per-core={}",
        "gpus_per_node": "--gpus-per-node={}",
        "account": "--account={}",
        "partition": "--partition={}",
    }

    _bind_options_map = {
        CpuBinding.BIND_NONE: ["--cpu-bind=none"],
        CpuBinding.BIND_SOCKETS: ["--cpu-bind=sockets"],
        CpuBinding.BIND_CORES: ["--cpu-bind=cores"],
        CpuBinding.BIND_THREADS: ["--cpu-bind=threads"],
        CpuBinding.BIND_USER: [],
    }

    _distribution_options_map = {
        None: "*",
        CpuDistribution.DISTRIBUTE_DEFAULT: "*",
        CpuDistribution.DISTRIBUTE_BLOCK: "block",
        CpuDistribution.DISTRIBUTE_CYCLIC: "cyclic",
    }

    def _get_distribution_options(self, job: Job) -> List[str]:
        """Return options for task distribution"""
        if (job.distribute_remote is None) and (job.distribute_local is None):
            return []

        distribute_remote = job.distribute_remote
        distribute_local = job.distribute_local

        if distribute_remote is CpuDistribution.DISTRIBUTE_USER:
            debug(
                (
                    "Not applying task distribution options because remote distribution"
                    " of tasks is set to use user-provided settings"
                )
            )
            return []
        if distribute_local is CpuDistribution.DISTRIBUTE_USER:
            debug(
                (
                    "Not applying task distribution options because local distribution"
                    " of tasks is set to use user-provided settings"
                )
            )
            return []

        return [
            (
                f"--distribution={self._distribution_options_map[distribute_remote]}"
                f":{self._distribution_options_map[distribute_local]}"
            )
        ]

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:
        executable = "srun"
        if env_pipeline is None:
            env_pipeline = DefaultEnvPipeline()
        else:
            env_pipeline = env_pipeline.copy(deep=True)

        flags = []

        for attr, option in self._job_options_map.items():
            value = getattr(job, attr, None)

            if value is not None:
                flags += [option.format(value)]

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
