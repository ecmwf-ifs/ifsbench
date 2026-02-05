# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
from pathlib import Path
from typing import List, Optional

from ifsbench.env import EnvPipeline
from ifsbench.job import Job
from ifsbench.launch.launcher import Launcher, LaunchData


class BashLauncher(Launcher):
    """
    :any:`Launcher` implementation that converts launch commands to bash scripts.
    session.

    This launcher wraps another launcher and puts the actual launch command in
    a bash script, using the path ``run_dir/bash_scripts/command_time.sh``.
    """

    #: The underlying launcher for the parallel launch.
    base_launcher: Launcher

    #: Flags for the underlying launcher.
    base_launcher_flags: List[str] = []

    def _write_bash_file(self, f, launch_data):
        f.write("#! /bin/bash\n\n")

        for key, value in launch_data.env.items():
            f.write(f'export {key}="{value}"\n')

        for c in launch_data.cmd:
            f.write(f'"{c}" ')

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:

        launch_data = self.base_launcher.prepare(
            run_dir=run_dir,
            job=job,
            cmd=cmd,
            library_paths=library_paths,
            env_pipeline=env_pipeline,
            custom_flags=self.base_launcher_flags
        )

        # Create the directory for the bash scripts.
        script_dir = run_dir/'bash_scripts'

        script_dir.mkdir(parents=True, exist_ok=True)

        # Always use UTC time and format it.
        time_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d:%H-%M-%S-%f')
        cmd_str = cmd[0]

        script_path = script_dir/f'{cmd_str}_{time_str}.sh'

        with script_path.open('w', encoding='utf-8') as f:
            self._write_bash_file(f, launch_data)

        return LaunchData(
            run_dir=run_dir,
            cmd=['/bin/bash', str(script_path)],
        )
