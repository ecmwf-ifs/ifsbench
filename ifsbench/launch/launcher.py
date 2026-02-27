# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Implementation of launch commands for various MPI launchers
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ifsbench.serialisation_mixin import (
    SubclassableSerialisationMixin,
)
from ifsbench.env import EnvPipeline
from ifsbench.job import Job
from ifsbench.logging import debug, info
from ifsbench.util import execute, ExecuteResult

__all__ = ['CompositeLauncher', 'LaunchData', 'Launcher']


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

    run_dir: Path
    cmd: List[str]
    env: dict = field(default_factory=dict)

    def launch(self) -> ExecuteResult:
        """
        Launch the actual executable.

        Returns
        -------
        ifsbench.ExecuteResult:
            The results of the execution.
        """

        info(f'Launch command {self.cmd} in {self.run_dir}.')

        debug('Environment variables:')
        for key, value in self.env.items():
            debug(f'\t{key}={value}')

        return execute(
            command=self.cmd,
            cwd=self.run_dir,
            env=self.env,
        )


class Launcher(SubclassableSerialisationMixin):
    """
    Abstract base class for launching parallel jobs.
    Subclasses must implement the prepare function.
    """

    # command line flags to pass to the laucher
    flags: List['str'] = []

    @abstractmethod
    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:
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


class LauncherWrapper(SubclassableSerialisationMixin):
    # command line flags to pass to the laucher
    flags: List['str'] = []

    @abstractmethod
    def wrap(
        self,
        launch_data: LaunchData,
        run_dir: Path,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
    ) -> LaunchData:
        """
        Wrap a Launch with additional features.

        Parameters
        ----------
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


class CompositeLauncher(Launcher):
    """
    Launcher implementation that allows adding different features to a base launcher.
    """

    # The launcher that provides the basic launch command.
    base_launcher: Launcher
    # Additional features that are added to the basic launch command.
    # Execution is in the order they are specified.
    wrappers: List[LauncherWrapper] = []

    def prepare(
        self,
        run_dir: Path,
        job: Job,
        cmd: List[str],
        library_paths: Optional[List[str]] = None,
        env_pipeline: Optional[EnvPipeline] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> LaunchData:
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
            Additional flags that are added to the base launcher command.

        Returns
        -------

        LaunchData
        """
        launch_data = self.base_launcher.prepare(
            run_dir, job, cmd, library_paths, env_pipeline, self.flags
        )
        for wrapper in self.wrappers:
            launch_data = wrapper.wrap(launch_data, run_dir, cmd, library_paths, env_pipeline)

        return launch_data
