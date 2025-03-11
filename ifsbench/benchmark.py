# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Generic benchmark implementation.
"""

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


__all__ = ['ScienceSetup', 'TechSetup', 'Benchmark']

@dataclass
class ScienceSetup:
    """
    Generic (scientific) benchmark setup.

    This dataclass encapsulates the information that is needed to describe a 
    benchmark:
      * The application that is benchmarked (unless overriden by :class:`TechSetup`).
      * The data pipeline.
      * The environment variables that are needed.

    This kind of information is called the ``scientific`` setup as it describes
    _what_ gets benchmarked and _how_.
    Additional technical details that don't alter results (debug flags, additional
    environment variables, etc.) should be specified in :class:`TechSetup`, instead.
    """
    #: The application that gets benchmarked (unless overriden by :class:`TechSetup`).
    application: Application

    #: Data handlers that are executed only once, during the initial setup
    #: of the run directory.
    data_handlers_init:  List[DataHandler] = field(default_factory=list)

    #: Data handlers that are executed every time the benchmark is run.
    data_handlers_runtime:  List[DataHandler] = field(default_factory=list)

    #: Environment handlers that are used when the benchmark is run.
    env_handlers:  List[EnvHandler] = field(default_factory=list)

@dataclass
class TechSetup:
    """
    Additional technical details for benchmarks.

    This dataclass can be used in combination with a :class:`ScienceSetup` 
    to setup a `Benchmark`. It encapsulates additional technical details 
    like debug flags, debug executables or performance-altering environment variables
    that do not change the results of the benchmark.
    """

    #: If set, this overrides the application that gets benchmarked.
    application: Optional[Application] = None

    #: Data handlers that are executed only once, during the initial setup
    #: of the run directory.
    data_handlers_init:  List[DataHandler] = field(default_factory=list)

    #: Data handlers that are executed every time the benchmark is run.
    data_handlers_runtime:  List[DataHandler] = field(default_factory=list)

    #: Environment handlers that are used for the initial data setup.
    env_handlers:  List[EnvHandler] = field(default_factory=list)

@dataclass
class Benchmark:
    """
    Generic benchmark implementation.

    This benchmark implementation can be used to
      1. Setup a run directory.
      2. Launch a given appliation in the run directory.
      3. Create a result object, using the data in the run directory.
    """

    #: The main (scientific) benchmark setup that describes _what_ gets benchmarked
    # and _which data_ is used.
    science: ScienceSetup

    #: Additional technical details that don't alter the results.
    tech: Optional[TechSetup] = None

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

        handlers = self.science.data_handlers_init
        if self.tech:
            handlers += self.tech.data_handlers_init

        for handler in handlers:
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

        env_pipeline = DefaultEnvPipeline(handlers=self.science.env_handlers, env_initial=os.environ)
        if self.tech:
            env_pipeline.add(self.tech.env_handlers)

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

        application = self.science.application
        if self.tech is not None and self.tech.application is not None:
            application = self.tech.application

        cmd = application.get_command(run_dir, job)

        library_paths = application.get_library_paths(run_dir, job)

        data_handlers = list(self.science.data_handlers_runtime)
        if self.tech:
            data_handlers += self.tech.data_handlers_runtime
        data_handlers += application.get_data_handlers(run_dir, job)

        for handler in data_handlers:
            handler.execute(run_dir)

        env_pipeline.add(application.get_env_handlers(run_dir, job))

        launch = launcher.prepare(run_dir, job, cmd, library_paths, env_pipeline, launcher_flags)
        launch.launch()
