# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from enum import Enum
import os
from typing import Dict, List, Optional, Union

from pydantic import Field, model_validator
from typing_extensions import Self

from ifsbench.serialisation_mixin import SubclassableSerialisationMixin, SerialisationMixin
from ifsbench.logging import debug

__all__ = ['EnvHandler', 'EnvOperation', 'EnvPipeline']


class EnvOperation(str, Enum):
    """
    Enum of environment operations.

    Specifies operations on environment variables.
    """

    #: Set a given environment variable.
    SET = 'set'

    #: Append to a given environment variable.
    APPEND = 'append'

    #: Prepend to a given environment variable.
    PREPEND = 'prepend'

    #: Delete/unset a given environment variable.
    DELETE = 'delete'

    #: Clear the whole environment.
    CLEAR = 'clear'


class EnvHandler(SerialisationMixin):
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

    mode: EnvOperation
    key: Optional[str] = None
    value: Optional[str] = None

    @model_validator(mode='after')
    def validate_value_for_mode(self) -> Self:
        if self.key is None and self.mode != EnvOperation.CLEAR:
            raise ValueError(f'The key must be specified for operation {self.mode}!')

        if self.value is None:
            if self.mode in (EnvOperation.APPEND, EnvOperation.PREPEND):
                raise ValueError(f'The value must be specified for operation {self.mode}!')
        return self

    def execute(self, env: Dict[str, str]) -> None:
        """
        Apply the stored changes to a given environment.

        Parameters
        ----------
        env: dict
            An environment dictionary. Will be updated in place.
        """

        if self.mode == EnvOperation.SET:
            debug(f'Set environment entry {self.key} = {self.value}.')
            env[self.key] = self.value
        elif self.mode == EnvOperation.APPEND:
            if env.get(self.key, None) is not None:
                env[self.key] += os.pathsep + self.value
            else:
                env[self.key] = self.value

            debug(f'Append {self.value} to environment variable {self.key}.')
        elif self.mode == EnvOperation.PREPEND:
            if env.get(self.key, None) is not None:
                env[self.key] = self.value + os.pathsep + env[self.key]
            else:
                env[self.key] = self.value

            debug(f'Prepend {self.value} to environment variable {self.key}.')

        elif self.mode == EnvOperation.DELETE:
            if self.key in env:
                debug(f'Delete environment variable {str(self.key)}.')
                del env[self.key]

        elif self.mode == EnvOperation.CLEAR:
            debug('Clear whole environment.')
            env.clear()


class EnvPipeline(ABC, SubclassableSerialisationMixin):
    """
    Abstract base class for environment update pipelines.

    Instances of this class can be used to update environment variables.
    EnvPipeline supports all list operations to add/remove EnvHandler objects.
    """

    @abstractmethod
    def execute(self) -> Dict[str, str]:
        """
        Create an environment using the pipeline.

        Returns
        -------
        dict:
            The created environment.
        """
        return NotImplemented

    @abstractmethod
    def add(self, handler: Union[EnvHandler, List[EnvHandler]]) -> None:
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

    handlers: List[EnvHandler] = Field(default_factory=list)
    env_initial: Optional[Dict[str, Optional[str]]] = Field(default_factory=dict)

    def add(self, handler: Union[EnvHandler, List[EnvHandler]]) -> None:
        if isinstance(handler, EnvHandler):
            self.handlers.append(handler)
        else:
            self.handlers += handler

    def execute(self) -> Dict[str, Optional[str]]:
        env = dict(self.env_initial)

        for handler in self.handlers:
            handler.execute(env)

        return env
