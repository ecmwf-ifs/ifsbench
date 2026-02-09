# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
click-based decorators for specifying launchers + launcher flags.
"""

from functools import wraps
from pathlib import Path
from typing import List, Optional, Tuple
import yaml

import click

from ifsbench.arch import Arch
from ifsbench.launch import (
    Launcher,
)
from ifsbench.serialisation_mixin import SerialisationMixin


class LauncherBuilder(SerialisationMixin):
    """
    Helper class to build the correct launcher.

    This class is used to combine
        * launcher-related command line arguments
        * default launchers/flags defined in Arch classes
    in order to create a final launcher object and launch flags.
    """

    #: Whether the srun launcher is used.
    launcher_config: Optional[str] = None

    #: Additional launcher flags that should be used.
    launcher_flags: List[str] = []

    def build_from_arch(
        self, arch: Optional[Arch] = None
    ) -> Tuple[Launcher, List[str]]:
        """
        Build a launcher, using information from an `Arch` object.
        """
        if arch:
            return self.build_launcher(
                default_launcher=arch.get_default_launcher(),
                default_launcher_flags=arch.default_launcher_flags,
            )
        return self.build_launcher()

    def build_launcher(
        self,
        default_launcher: Optional[Launcher] = None,
        default_launcher_flags: Optional[List[str]] = None,
    ) -> Tuple[Launcher, List[str]]:
        """
        Build a launcher using a given default launcher and default flags.
        """

        if self.launcher_config:

            with Path(self.launcher_config).open("r", encoding="utf-8") as f:
                loaded_yaml = yaml.safe_load(f)
            launcher = Launcher.from_config(loaded_yaml)
            launcher.flags += self.launcher_flags
            return launcher, launcher.flags

        if default_launcher:
            if not default_launcher_flags:
                default_launcher_flags = []
            default_launcher.flags += default_launcher_flags + self.launcher_flags
        return default_launcher, default_launcher_flags + self.launcher_flags


def launcher_options(func):
    """
    Decorator for use in click.commands to set launcher options.

    Addd a couple of flags to
        * specify different launchers
        * add launcher flags

    This decorator passes the different options as a `LauncherBuilder` object
    to the click.command-decorated function using the `launcher_builder`
    argument name.
    """

    @click.option(
        "--launcher-config",
        type=str,
        default=None,
        help="yaml file containing launcher configuration",
    )
    @click.option(
        "--launcher-flags",
        "-f",
        default=[],
        multiple=True,
        type=str,
        help="Additional launcher flags",
    )
    @click.pass_context
    @wraps(func)
    def process_launcher(ctx, *args, **kwargs):
        builder = LauncherBuilder()

        builder.launcher_config = kwargs.pop("launcher_config")

        builder.launcher_flags = kwargs.pop("launcher_flags")

        return ctx.invoke(func, *args, **kwargs, launcher_builder=builder)

    return process_launcher
