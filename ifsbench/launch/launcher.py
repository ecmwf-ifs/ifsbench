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
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from pydantic import model_validator, TypeAdapter, Field
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from typing_extensions import Annotated

from ifsbench.config_mixin import PydanticConfigMixin
from ifsbench.env import EnvPipeline
from ifsbench.job import Job
from ifsbench.logging import debug, info
from ifsbench.util import execute, ExecuteResult

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

        info(f"Launch command {self.cmd} in {self.run_dir}.")

        debug("Environment variables:")
        for key, value in self.env.items():
            debug(f"\t{key}={value}")

        return execute(
            command=self.cmd,
            cwd=self.run_dir,
            env=self.env,
        )


class Launcher(PydanticConfigMixin):
    """
    Abstract base class for launching parallel jobs.
    Subclasses must implement the prepare function.
    """

    # launcher_type is used to distinguish Launcher subclasses and has
    # to be defined in all subclasses.
    launcher_type: str

    _subclasses: ClassVar[Dict[str, Type[Any]]] = {}
    _discriminating_type_adapter: ClassVar[TypeAdapter]

    @model_validator(mode='wrap')
    @classmethod
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> 'Launcher':
        if cls is Launcher:
            return Launcher._discriminating_type_adapter.validate_python(v)
        return handler(v)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        Launcher._subclasses[cls.model_fields['launcher_type'].default] = cls
        Launcher._discriminating_type_adapter = TypeAdapter(
            Annotated[
                Union[tuple(Launcher._subclasses.values())],
                Field(discriminator='launcher_type'),
            ]
        )

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
