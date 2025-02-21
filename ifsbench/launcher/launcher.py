# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Implementation of launch commands for various MPI launchers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ifsbench.logging import debug, info
from ifsbench.util import execute

__all__ = ['LaunchData', 'Launcher']


@dataclass
class LaunchData:
    """
    Dataclass that contains all data necessary for launching a command.

    Class variables
    ---------------

    run_dir: Path
        The working directory for launching.
    cmd: list[str]
        The command that gets launched.
    env: dict[str,str]
        The environment variables that are used.
    """
    run_dir : Path
    cmd : list[str]
    env: dict = field(default_factory=dict)

    def launch(self):
        """
        Launch the actual executable.
        """

        info(f"Launch command {self.cmd} in {self.run_dir}.")

        debug("Environment variables:")
        for key, value in self.env.items():
            debug(f"\t{key}={value}")


        execute(
            command = self.cmd,
            cwd = self.run_dir,
            env = self.env
        )

class Launcher(ABC):
    """
    Abstract base class for launching parallel jobs.
    Subclasses must implement the prepare function.
    """

    @abstractmethod
    def prepare(self, run_dir, job, cmd, library_paths=None, env_pipeline=None, custom_flags=None):
        """
        Prepare a launch by building a LaunchData object (which in turn can
        perform the actual launch).

        Parameters
        ----------
        run_dir: Path
            The working directory for launching.
        job: Job
            The job object that holds all necessary parallel data.
        cmd: list[str]
            The command that should be launched.
        library_paths: list[Path]
            Additional library paths that are needed for launching.
        env_pipeline: EnvPipeline
            Pipeline for modifying environment variables.
        custom_flags: list[str]
            Additional flags that are added to the launcher command.

        Returns
        -------

        LaunchData
        """
        return NotImplemented
