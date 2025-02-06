# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
from pathlib import Path

from ifsbench.launcher.launcher import Launcher, LaunchData

class BashLauncher(Launcher):
    """
    UNTESTED!

    This launcher encapsulates another launcher and creates a bash file
    `run_dir/<path>/launch_<executable>_<date>.sh` which is then executed.

    Parameters
    ----------
    script_dir: str or :any:`pathlib.Path`
        The directory where the resulting bash script is placed. If a relative path
        is given, this will be relative to the ``run_dir`` argument in
        :meth:`prepare`.
    base_launcher : Launcher
        The underlying launcher that is used to generate the launch command.
    base_launcher_flags: list[str] or None
        Additional flags that are passed to the ``base_launcher``.
    """

    def __init__(self, script_dir, base_launcher, base_launcher_flags=None):
        self._script_dir = Path(script_dir)
        self._base_launcher = base_launcher
        self._base_launcher_flags = base_launcher_flags

    def prepare(self, run_dir, job, cmd, library_paths=None, env_pipeline=None, custom_flags=None):
        child_data = self._base_launcher.prepare(run_dir, job, cmd, library_paths,
            env_pipeline, self._base_launcher_flags)

        if self._script_dir.is_absolute():
            script_dir = self._script_dir
        else:
            script_dir = run_dir/self._script_dir

        if script_dir.exists() and script_dir.is_file():
            script_dir.unlink()

        script_dir.mkdir(exist_ok=True, parents=True)

        current_datetime = datetime.datetime.now()
        timestamp = current_datetime.strftime('%Y-%m-%d.%H:%M:%S.%f')

        # Guess the executable name from the command.
        exec_name = cmd[0].split('/')[-1]
        path = script_dir/f"run-{exec_name}-{timestamp}.sh"

        run_env = child_data.env

        with path.open('w') as f:
            f.write('#! /bin/bash')
            f.write("\n")

            for key, value in run_env.items():
                f.write(f"export {key}={value}\n")

            f.write("\n")

            f.write(' '.join(child_data.cmd))

        return LaunchData(
            cmd=['/bin/bash', str(path)],
            run_dir=run_dir,
            env={}
        )
