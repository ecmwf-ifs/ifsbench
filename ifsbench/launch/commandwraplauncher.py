# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from copy import deepcopy
from pathlib import Path
from typing import List, Optional

from ifsbench.env import EnvPipeline
from ifsbench.launch.launcher import LauncherWrapper, LaunchData


class CommandWrapLauncher(LauncherWrapper):
    """
    :any:`LauncherWrapper` implementation that appends/prepends to the launch
    command of another launcher.

    The resulting launch command will be
        prepend_flags + original_command + flags + append_flags.
    """

    #: List of flags/commands that are prepended to the launch command.
    prepend_flags: List[str] = []

    #: List of flags/commands that are appended to the launch command.
    append_flags: List[str] = []

    def wrap(
        self,
        launch_data: LaunchData,
        run_dir: Path,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
    ) -> LaunchData:

        launch_data = deepcopy(launch_data)

        launch_data.cmd = self.prepend_flags + launch_data.cmd + self.flags + self.append_flags

        return launch_data
