# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import List, Optional

from ifsbench.application import Application
from ifsbench.arch import Arch
from ifsbench.data import DataHandler
from ifsbench.env import EnvHandler, DefaultEnvPipeline
from ifsbench.job import Job
from ifsbench.launch import Launcher


__all__ = ['DefaultBenchmarkSetup', 'DefaultBenchmark']

@dataclass
class DefaultBenchmarkSetup:
    """
    Generic benchmark setup.

    This dataclass holds generic information that is needed by benchmarks.
    """

    #: The data pipeline for the initial data setup.
    data_handlers:  List[DataHandler] = field(default_factory=list)

    #: Environment handlers that are used for the initial data setup.
    env_handlers:  List[EnvHandler] = field(default_factory=list)

    #: The application that gets benchmarked.
    application: Optional[Application] = None

    def merge(self, other):
        """
        Create a copy of this object and merge it with another given setup
        object by
        * appending the data_handlers
        * appending the env_handlers
        * replacing the application with ``other.application`` (if specified).

        Parameters
        ----------
        other: DefaultBenchmarkSetup
            The other setup object that is merged into this one.

        Returns
        -------
        The merged object.
        """
        data_handlers = self.data_handlers + other.data_handlers
        env_handlers = self.env_handlers + other.env_handlers
        application = self.application
        if other.application:
            application = other.application

        return DefaultBenchmarkSetup(
            data_handlers = data_handlers,
            env_handlers = env_handlers,
            application = application
        )

class DefaultBenchmark:
    """
    Generic benchmark implementation.

    This benchmark implementation can be used to
      1. Setup a run directory.
      2. Launch a given appliation in the run directory.
      3. Create a result object, using the data in the run directory.

    Parameters
    ----------
    setup: DefaultBenchmarkSetup
        The generic benchmark setup.
    tech_setup: DefaultBenchmarkSetup or None
        If given, an additional DefaultBenchmarkSetup object that can provide
        additional, technical information (additional debug environment flags).
    """
    def __init__(self,
        setup: DefaultBenchmarkSetup,
        tech_setup: Optional[DefaultBenchmarkSetup] = None
    ):
        self._setup = setup

        if tech_setup:
            self._setup = self._setup.merge(tech_setup)


    def setup_rundir(self,
        run_dir: Path,
        force: bool = False
    ):
        """
        Setup the run directory.

        This creates the run directory and executes all data handlers in the
        benchmark setup to populate it.

        Parameters
        ----------

        run_dir: pathlib.Path
            The path to the run directory.

        force: bool
            If True, always execute the full data pipeline.
            If False, only execute the data handlers if the run directory is
            empty.
        """
        exists = run_dir.exists() and any(run_dir.iterdir())

        if exists and not force:
            return

        for handler in self._setup.data_handlers:
            handler.execute(run_dir)


    def run(self,
        run_dir: Path,
        job: Job,
        arch: Optional[Arch] = None,
        launcher: Optional[Launcher] = None,
        launcher_flags: Optional[List[str]] = None
    ):
        """
        Run the benchmark.

        Parameters
        ----------
        run_dir: pathlib.Path
            The path to the run directory.
        job: Job
            The parallel setup for the benchmark.
        arch: Arch
            A specific architecture that is used.
        launcher: Launcher
            A custom launcher to use. If None, the arch launcher is used.
        launcher_flags: list[str]
            Additional flags to be added to the launcher invocation.
        """

        env_pipeline = DefaultEnvPipeline(handlers=self._setup.env_handlers, env_initial=os.environ)

        if arch:
            arch_result = arch.process_job(job)

            if arch_result.env_handlers:
                env_pipeline.add(arch_result.env_handlers)

            job = arch_result.job
            if launcher is None:
                launcher = arch_result.default_launcher
            if launcher_flags is None:
                launcher_flags = arch_result.default_launcher_flags

        if launcher is None:
            raise ValueError("No launcher was specified!")

        cmd = self._setup.application.get_command(run_dir, job)
        library_paths = self._setup.application.get_library_paths(run_dir, job)

        for handler in self._setup.application.get_data_handlers(run_dir, job):
            handler.execute(run_dir)

        for handler in self._setup.application.get_env_handlers(run_dir, job):
            env_pipeline.add(handler)

        launch = launcher.prepare(run_dir, job, cmd, library_paths, env_pipeline, launcher_flags)
        launch.launch()
