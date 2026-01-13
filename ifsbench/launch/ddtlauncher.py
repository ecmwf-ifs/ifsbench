# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import List, Optional

from ifsbench.env import EnvPipeline
from ifsbench.job import Job
from ifsbench.launch.launcher import Launcher, LaunchData


class DDTLauncher(Launcher):
    """
    :any:`Launcher` implementation that launches straight into a Linaro DDT
    session.
    """

    #: The underlying launcher for the parallel launch.
    base_launcher: Launcher

    #: Flags for the underlying launcher.
    base_launcher_flags: List[str] = []

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:

        # Just use the underlying launcher to create the launch data and modify
        # it later.
        launch_data = self.base_launcher.prepare(
            run_dir=run_dir,
            job=job,
            cmd=cmd,
            library_paths=library_paths,
            env_pipeline=env_pipeline,
            custom_flags=self.base_launcher_flags
        )

        if custom_flags is None:
            custom_flags = []

        # Prepend the launch command with ddt and all ddt flags.
        launch_data.cmd = ['ddt'] + custom_flags + ['--'] + launch_data.cmd

        return launch_data
