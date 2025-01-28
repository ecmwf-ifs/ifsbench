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
from dataclasses import dataclass, field
from typing import List

from ifsbench.env import EnvHandler
from ifsbench.launcher.launcher import Launcher

__all__ = ['Arch', 'DefaultArch']

@dataclass
class ArchResult:
    """
    Holds results of an :meth:`Arch.process` run.

    Attributes:
    job: Job
        The updated job after the architecture processing.
    env_handlers: list[EnvHandler]
        Additional EnvHandler objects that set architecture-specific environment
        flags.
    default_launcher: Launcher
        The default launcher that is used on this system.
    default_launcher_flags : list[str]
        Additional launcher flags that should be added to launcher invocations.
    """
    job = None
    env_handlers : List[EnvHandler] = field(default_factory=list)
    default_launcher : Launcher = None
    default_launcher_flags : List[str] = field(default_factory=list)


class Arch(ABC):
    """
    Architecture/system description.

    Additional machine/software environment information that is used to run jobs.
    It provides information about the parallel setup (number of cores per node,
    available GPUs, etc.) as well as system-specific environment variables.
    """

    @abstractmethod
    def get_default_launcher(self):
        """
        Return the launcher that is usually used on this system (e.g.
        SLURM, PBS, MPI).

        Returns
        -------
        Launcher
            The default launcher used in this architecture.
        """
        return NotImplemented

    @abstractmethod
    def get_cpu_configuration(self):
        """
        Return the hardware setup that is used.

        Returns
        -------
        CpuConfiguration
        """
        return NotImplemented


    @abstractmethod
    def process_job(self, job, **kwargs):
        """
        Process a given job and add architecture-dependent tweaks. This will
        return a :class:`ArchResult` object that
        * holds an updated Job object.
        * may specify additional EnvHandler objects needed on this architecture.
        * may specify additional flags that should be passed to the default
          launcher.

        Parameters
        ----------
        job: Job
            The initial job specification. This object is not updated.

        Returns
        -------
        ArchResult
        """
        return NotImplemented

class DefaultArch(Arch):

    def __init__(self, launcher, cpu_config, set_explicit=False,
                 account=None, partition=None):
        """
        Default architecture that can be used for various systems.

        Parameters
        ----------
        launcher : Launcher
            The default launcher that is used on this system.
        cpu_config : CpuConfiguration
            The hardware setup of the system.
        set_explicit : bool
            If set to True, the following attributes in result.job are
            calculated and set explicitly, using ``cpu_config``:
                * tasks
                * nodes
                * tasks_per_node
            If not, these values will stay None, if not specified.
        account : str
            The account that is passed to the launcher.
        partition : str
            The partition that will be passed to the launcher.
        """
        self._cpu_config = cpu_config
        self._launcher = launcher
        self._set_explicit = bool(set_explicit)
        self._account = account
        self._partition = partition

    def get_default_launcher(self):
        return self._launcher

    def get_cpu_configuration(self):
        return self._cpu_config

    def process_job(self, job, **kwargs):
        result = ArchResult()

        account = self._account
        partition = self._partition

        result.job = job.copy()

        if partition:
            result.job.set('partition', partition)
        if account:
            result.job.set('account', account)

        if self._set_explicit:
            result.job.calculate_missing(self._cpu_config)

        result.default_launcher = self.get_default_launcher()

        return result

