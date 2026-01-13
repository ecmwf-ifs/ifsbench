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
from typing import List, Optional, Tuple

import click

from ifsbench.arch import Arch
from ifsbench.launch import Launcher, BashLauncher, DirectLauncher, DDTLauncher, MpirunLauncher, SrunLauncher
from ifsbench.logging import warning
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
    launcher_srun: bool = False

    #: Whether the mpirun launcher is used.
    launcher_mpirun: bool = False

    #: The executable that is used in the direct launcher (direct launcher
    # isn't used if value is None).
    launcher_direct: Optional[str] = None

    #: Whether the DDT debugger is used.
    debug_ddt: bool = False

    #: Additional launcher flags that should be passed to the debug launcher.
    debug_launcher_flags: List[str] = []

    #: Additional launcher flags that should be used.
    add_launcher_flags: List[str] = []

    #: Launcher flags that should replace the flags used by `launcher`.
    launcher_flags: Optional[List[str]] = None

    #: Whether the whole launch command is put into a bash file.
    bash: bool = False

    def build_from_arch(self, arch: Optional[Arch] = None) -> Tuple[Launcher, List[str]]:
        """
        Build a launcher, using information from an `Arch` object.
        """
        if arch:
            return self.build_launcher(
                default_launcher=arch.get_default_launcher(),
                default_launcher_flags=arch.default_launcher_flags
            )
        return self.build_launcher()

    def build_launcher(self,
        default_launcher: Optional[Launcher]=None,
        default_launcher_flags: Optional[List[str]]=None
        ) -> Tuple[Launcher, List[str]] :
        """
        Build a launcher using a given default launcher and default flags.
        """

        if default_launcher_flags is None:
            default_launcher_flags = []

        launcher = default_launcher


        if self.launcher_srun:
            launcher = SrunLauncher()
        if self.launcher_mpirun:
            launcher = MpirunLauncher()
        if self.launcher_direct is not None:
            if self.launcher_direct:
                launcher = DirectLauncher(executable=self.launcher_direct)
            else:
                launcher = DirectLauncher()

        if [self.launcher_srun, self.launcher_mpirun, self.launcher_direct is not None].count(True) > 1:
            warning(f"More than one launcher was activated on the command line! {type(launcher)} will be used!")

        if launcher is None:
            return None, []

        launcher_flags = default_launcher_flags + self.add_launcher_flags
        if self.launcher_flags is not None:
            launcher_flags = list(self.launcher_flags)

        if self.debug_ddt:
            launcher = DDTLauncher(
                base_launcher=launcher,
                base_launcher_flags=launcher_flags
            )

            launcher_flags = self.debug_launcher_flags

        if self.bash:
            launcher = BashLauncher(
                base_launcher=launcher,
                base_launcher_flags=launcher_flags
            )

            launcher_flags = []

        return launcher, launcher_flags

def launcher_options(func):
    """
    Decorator for use in click.commands to set launcher options.

    Addd a couple of flags to
        * specify different launchers
        * use different debug launchers
        * add/replace launcher flags

    This decorator passes the different options as a `LauncherBuilder` object
    to the click.command-decorated function using the `launcher_builder`
    argument name.
    """
    @click.option('--launcher-mpirun', is_flag=True, help="Use the default mpirun launcher")
    @click.option('--launcher-srun', is_flag=True, help="Use the default srun Launcher")
    @click.option('--launcher-direct', type=str, default=None, help="Use the given executable to launch")
    @click.option('--debug-ddt', is_flag=True, help="Use the DDTLauncher debugger")
    @click.option('--bash', is_flag=True, help="Write all launches as bash scripts")
    @click.option('--replace-launcher-flags/--add-launcher-flags', 'replace', default=False,
        help="Whether launcher-flags replaces or adds to existing flags (default: add)")
    @click.option('--launcher-flags', default=[], multiple=True, type=str,
        help="Replace the base launcher flags by these flags")
    @click.option('--debug-launcher-flags', default=[], multiple=True, type=str,
        help="Add additional flags to debug launchers")
    @click.pass_context
    @wraps(func)
    def process_launcher(ctx, *args, **kwargs):
        builder = LauncherBuilder()

        builder.launcher_mpirun = kwargs.pop('launcher_mpirun')
        builder.launcher_srun = kwargs.pop('launcher_srun')
        builder.launcher_direct = kwargs.pop('launcher_direct')

        builder.debug_ddt = kwargs.pop('debug_ddt')

        launcher_flags = kwargs.pop('launcher_flags')
        replace = kwargs.pop('replace')
        if replace:
            builder.launcher_flags = launcher_flags
        else:
            builder.add_launcher_flags = launcher_flags

        builder.debug_launcher_flags = kwargs.pop('debug_launcher_flags')

        builder.bash = kwargs.pop('bash')

        return ctx.invoke(func, *args, **kwargs,
            launcher_builder=builder)

    return process_launcher
