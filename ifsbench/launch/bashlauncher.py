# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from copy import deepcopy
import datetime
import re
from pathlib import Path
from typing import List, Optional, TextIO

from ifsbench.env import EnvPipeline
from ifsbench.launch.launcher import LauncherWrapper, LaunchData
from ifsbench.logging import debug


class BashLauncher(LauncherWrapper):
    """
    :any:`Launcher` implementation that converts launch commands to bash scripts.
    session.

    This launcher wraps another launcher and puts the actual launch command in
    a bash script, using the path ``run_dir/bash_scripts/command_time.sh``.
    """

    def _write_header(self, f: TextIO, header: str):
        """
        Write a "header" to a file. A header is simply a comment of the form

        ############
        # The header
        ###########
        """
        f.write("\n")
        f.write('#' * 60)
        f.write("\n")
        f.write(f'# {header}')
        f.write("\n")
        f.write('#' * 60)
        f.write("\n")
        f.write("\n")

    def _write_bash_file(self, f: TextIO, launch_data: LaunchData):
        """
        Write the content of a LaunchData object to a bash script.
        """
        f.write("#! /bin/bash\n\n")

        self._write_header(f, "Specify environment")
        env_name_check = re.compile(r'[a-zA-Z_][a-zA-Z_0-9]*')

        for key, value in launch_data.env.items():
            # Check that the current "environment variable" is an actual
            # variable. For example, bash function definitions may be in
            # `launch_data.env` but end with `_%%` and are not proper
            # environment variables. We skip these.
            if not env_name_check.fullmatch(key):
                debug(f'Ignore non-standard bash name {key} in BashLauncher.')
                continue

            # We set the environment variables inside a "..." block. This means
            # that we have to escpae certain special characters (", $, `).
            escaped_value = value.replace('$', '\\$')
            escaped_value = escaped_value.replace('"', '\\"')
            escaped_value = escaped_value.replace('`', '\\`')
            f.write(f'export {key}="')
            f.write(escaped_value)
            f.write("\"\n")

        self._write_header(f, "Specify launch command")

        f.write(f'cd "{launch_data.run_dir}"')
        f.write("\n")
        for c in launch_data.cmd:
            f.write(f'"{c}" ')

    def wrap(
        self,
        launch_data: LaunchData,
        run_dir: Path,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
    ) -> LaunchData:

        launch_data = deepcopy(launch_data)
        # Create the directory for the bash scripts.
        script_dir = run_dir / "bash_scripts"

        script_dir.mkdir(parents=True, exist_ok=True)

        # Always use UTC time and format it.
        time_str = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d:%H-%M-%S-%f"
        )
        cmd_str = cmd[0].split('/')[-1]

        script_path = script_dir / f"{cmd_str}_{time_str}.sh"

        with script_path.open("w", encoding="utf-8") as f:
            self._write_bash_file(f, launch_data)

        return LaunchData(
            run_dir=run_dir,
            cmd=["/bin/bash", str(script_path)],
        )
