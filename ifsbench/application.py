# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod

__all__ = ['Application', 'DefaultApplication']

class Application(ABC):
    """
    Base class for applications that can be launched.
    """

    @abstractmethod
    def get_data_handlers(self, run_dir, job):
        """
        Return necessary data handlers.

        Return all application-specific handler objects that must be run before
        launching the executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[DataHandler]:
            List of DataHandler objects.
        """
        return NotImplemented

    @abstractmethod
    def get_env_handlers(self, run_dir, job):
        """
        Return necessary environment handlers.

        Return all application-specific environment handler objects that are
        needed for launching the executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[EnvHandler]:
            List of EnvHandler objects.
        """
        return NotImplemented

    @abstractmethod
    def get_library_paths(self, run_dir, job):
        """
        Return necessary library paths.

        Return all library paths that are required to launch this executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[pathlib.Path]:
            List of the library paths.
        """
        return NotImplemented

    @abstractmethod
    def get_command(self, run_dir, job):
        """
        Return the corresponding command.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[str]:
            The command and (if necessary) corresponding flags.
        """
        return NotImplemented


class DefaultApplication(Application):
    """
    Default application implementation.

    Simple implementation of the application class where all returned data is
    static and doesn't depend on the ``run_dir`` or ``job`` parameters.

    Parameters
    ----------
    command: list[str]
        The command that corresponds to this application.
    data_handlers: list[DataHandler]
        The DataHandler list that is returned by get_data_handlers.
    env_handlers: list[EnvHandler]
        The EnvHandler list that is returned by get_env_handlers.
    library_paths: list[pathlib.Path]
        The library path list that is returned by get_library_paths.
    """

    def __init__(self, command, data_handlers=None, env_handlers=None, library_paths=None):
        self._command = list(command)

        if data_handlers:
            self._data_handlers = list(data_handlers)
        else:
            self._data_handlers = []

        if env_handlers:
            self._env_handlers = list(env_handlers)
        else:
            self._env_handlers = []

        if library_paths:
            self._library_paths = list(library_paths)
        else:
            self._library_paths = []

    def get_data_handlers(self, run_dir, job):
        return list(self._data_handlers)

    def get_env_handlers(self, run_dir, job):
        return list(self._env_handlers)

    def get_library_paths(self, run_dir, job):
        return list(self._library_paths)

    def get_command(self, run_dir, job):
        return list(self._command)
