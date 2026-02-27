# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Architecture specifications
"""

from abc import ABC, abstractmethod
from typing import List

from ifsbench.serialisation_mixin import SubclassableSerialisationMixin, SerialisationMixin
from ifsbench.env import EnvHandler
from ifsbench.job import CpuConfiguration, Job
from ifsbench.launch.launcher import Launcher

__all__ = ['Arch', 'DefaultArch']


class ArchResult(SerialisationMixin):
    """
    Holds results of an :meth:`Arch.process` run.
    """

    #: The updated job after the architecture processing.
    job: Job = None

    #: Additional EnvHandler objects that set architecture-specific environment flags.
    env_handlers: List[EnvHandler] = []

    #: The default launcher that is used on this system.
    default_launcher: Launcher = None

    #: Additional launcher flags that should be added to launcher invocations.
    default_launcher_flags: List[str] = []


class Arch(ABC, SubclassableSerialisationMixin):
    """
    Architecture/system description.

    Additional machine/software environment information that is used to run jobs.
    It provides information about the parallel setup (number of cores per node,
    available GPUs, etc.) as well as system-specific environment variables.
    """

    @abstractmethod
    def get_default_launcher(self) -> Launcher:
        """
        Return the launcher that is usually used on this system (e.g.
        SLURM, PBS, MPI).

        Returns
        -------
        Launcher
            The default launcher used in this architecture.
        """

    @abstractmethod
    def get_default_launcher_flags(self) -> List[str]:
        """
        Return additional default launcher flags that belong to the default
        launcher.

        Returns
        -------
        List[str]
            The additional default launcher flags.
        """

    @abstractmethod
    def get_cpu_configuration(self) -> CpuConfiguration:
        """
        Return the hardware setup that is used.

        Returns
        -------
        CpuConfiguration
        """

    @abstractmethod
    def process_job(self, job: Job, **kwargs):
        """
        Process a given job and add architecture-dependent tweaks.

        This will return a :class:`ArchResult` object that

        * holds an updated Job object.
        * may specify additional EnvHandler objects needed on this architecture.
        * may specify additional flags that should be passed to the default launcher.

        Parameters
        ----------
        job: Job
            The initial job specification. This object is not updated.

        Returns
        -------
        ArchResult
        """


class DefaultArch(Arch):
    #: The default launcher that is used on this system
    launcher: Launcher

    #: The hardware setup of the system.
    cpu_config: CpuConfiguration

    #: If set to True, the following attributes in result.job are
    #:     calculated and set explicitly, using ``cpu_config``:
    #:         * tasks
    #:         * nodes
    #:         * tasks_per_node
    #:     If not, these values will stay None, if not specified.
    set_explicit: bool = False

    #: Additional flags that are passed to the launcher.
    launcher_flags: List[str] = []

    #: Additional environment handlers that are passed to the launcher.
    env_handlers: List[EnvHandler] = []

    def get_default_launcher(self) -> Launcher:
        return self.launcher

    def get_default_launcher_flags(self) -> List[str]:
        return self.launcher_flags

    def get_cpu_configuration(self) -> CpuConfiguration:
        return self.cpu_config

    def process_job(self, job: Job, **kwargs) -> ArchResult:
        result = ArchResult()

        result.job = job.clone()

        if self.set_explicit:
            result.job.calculate_missing(self.get_cpu_configuration())

        result.default_launcher = self.get_default_launcher()
        result.default_launcher_flags = list(self.launcher_flags)
        result.env_handlers = list(self.env_handlers)

        return result
