# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from collections import UserList
from enum import auto, Enum
import os

from ifsbench.logging import debug

__all__ = ['EnvHandler', 'EnvOperation', 'EnvPipeline']


class EnvOperation(Enum):
    """
    Enum of environment operations.

    Specifies operations on environment variables.

    Attributes
    ----------

    SET
        Set a given environment variable.
    APPEND
        Append to a given environment variable.
    PREPEND
        Prepend to a given environment variable.
    DELETE
        Delete/unset a given environment variable.
    CLEAR
        Clear the whole environment
    """
    SET = auto()
    APPEND = auto()
    PREPEND = auto()
    DELETE = auto()
    CLEAR = auto()

class EnvHandler:
    """
    Specify changes to environment variables.

    Parameters
    ----------
    mode: EnvOperation
        The operation that will be performed.
    key: str
        The name of the environment variable that is updated. Must be specified
        unless mode == CLEAR.
    value: str
        The value that is used for the operation. Must be specified unless
        mode in (SET, DELETE, CLEAR).

    Raises
    ------
    ValueError
        If key or value is None but must be specifed.
    """

    def __init__(self, mode, key=None, value=None):
        if key is not None:
            self._key = str(key)
        else:
            self._key = None

        if value is not None:
            self._value = str(value)
        else:
            self._value = None

        self._mode = mode

        if self._key is None and self._mode != EnvOperation.CLEAR:
            raise ValueError(f"The key must be specified for operation {mode.name}!")

        if self._value is None:
            if self._mode in (EnvOperation.APPEND, EnvOperation.PREPEND):
                raise ValueError(f"The value must be specified for operation {mode.name}!")

    def execute(self, env):
        """
        Apply the stored changes to a given environment.

        Parameters
        ----------
        env: dict
            An environment dictionary. Will be updated in place.
        """

        if self._mode == EnvOperation.SET:
            debug(f"Set environment entry {self._key} = {self._value}.")
            env[self._key] = self._value
        elif self._mode == EnvOperation.APPEND:
            if env.get(self._key, None) is not None:
                env[self._key] += os.pathsep + self._value
            else:
                env[self._key] = self._value

            debug(f"Append {self._value} to environment variable {self._key}.")
        elif self._mode == EnvOperation.PREPEND:
            if env.get(self._key, None) is not None:
                env[self._key] = self._value + os.pathsep + env[self._key]
            else:
                env[self._key] = self._value

            debug(f"Prepend {self._value} to environment variable {self._key}.")

        elif self._mode == EnvOperation.DELETE:
            if self._key in env:
                debug(f"Delete environment variable {str(self._key)}.")
                del env[self._key]

        elif self._mode == EnvOperation.CLEAR:
            debug('Clear whole environment.')
            env.clear()

class EnvPipeline(ABC, UserList):
    """
    Abstract base class for environment update pipelines.

    Instances of this class can be used to update environment variables.
    EnvPipeline supports all list operations to add/remove EnvHandler objects.
    """

    @abstractmethod
    def execute(self):
        """
        Create an environment using the pipeline.

        Returns
        -------
        dict:
            The created environment.
        """
        return NotImplemented

    @abstractmethod
    def add(self, handler):
        """
        Add new EnvHandlers to the pipeline.

        Parameters
        ----------
        handler: EnvHandler or list[EnvHandler]
            Handler(s) that are added.
        """

class DefaultEnvPipeline(EnvPipeline):
    """
    Default environment pipeline.

    Parameters
    ----------
    handlers: list[EnvHandler]
        The environment operations that should be incorporated.
    env_initial: dict or None
        The initial environment. If None, an empty environment is used.

    Raises
    ------
    ValueError:
        If overrides contains entries that are not EnvOverride objects.
    """

    def __init__(self, handlers=None, env_initial=None):
        if handlers:
            self._handlers = list(handlers)
        else:
            self._handlers = []

        for handler in self._handlers:
            if not isinstance(handler, EnvHandler):
                raise ValueError("Only EnvHandler objects are accepted!")

        if env_initial is not None:
            self._env_initial = dict(env_initial)
        else:
            self._env_initial = {}

    def add(self, handler):
        if isinstance(handler, EnvHandler):
            self._handlers.append(handler)
        else:
            self._handlers += handler

    def execute(self):
        env = dict(self._env_initial)

        for handler in self._handlers:
            handler.execute(env)

        return env
