# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import List, Optional

from ifsbench.env import DefaultEnvPipeline, EnvOperation, EnvPipeline, EnvHandler
from ifsbench.job import Job
from ifsbench.launch.launcher import Launcher, LaunchData


class DirectLauncher(Launcher):
    """
    :any:`Launcher` implementation that uses user-provided executables and flags.
    """

    #: The executable that is used to launch a command. If None is given,
    #: flags will be ignored and the command is executed directly.
    executable: Optional[str] = None

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:
        if env_pipeline is None:
            env_pipeline = DefaultEnvPipeline()
        else:
            env_pipeline = env_pipeline.copy(deep=True)

        if library_paths:
            for path in library_paths:
                env_pipeline.add(
                    EnvHandler(mode=EnvOperation.APPEND, key='LD_LIBRARY_PATH', value=str(path))
                )

        if self.executable:
            full_cmd = [self.executable]
        else:
            full_cmd = []

        full_cmd += self.flags

        if custom_flags:
            full_cmd += custom_flags

        full_cmd += cmd

        env = env_pipeline.execute()

        return LaunchData(run_dir=run_dir, cmd=full_cmd, env=env)
