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


class DDTLauncher(LauncherWrapper):
    """
    :any:`Launcher` implementation that launches straight into a Linaro DDT
    session.
    """

    def wrap(
        self,
        launch_data: LaunchData,
        run_dir: Path,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
    ) -> LaunchData:

        launch_data = deepcopy(launch_data)
        # Prepend the launch command with ddt and all ddt flags.
        launch_data.cmd = ['ddt'] + self.flags + ['--'] + launch_data.cmd

        return launch_data
