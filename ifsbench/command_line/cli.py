# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Common options and utilities for ifsbench run-scripts and CLI
"""

from functools import wraps
from logging import FileHandler
import sys

import click

from ifsbench.logging import logger, DEBUG
from ifsbench.util import auto_post_mortem_debugger


__all__ = ['cli', 'RunOptions', 'run_options', 'ReferenceOptions', 'reference_options']


@click.group()
@click.option('--debug/--no-debug', 'debug_', default=False, show_default=True,
              help='Enable / disable debug mode with verbose logging.')
@click.option('--log', type=click.Path(writable=True),
              help='Write debug-level information to a log file.')
@click.option('--pdb', 'pdb_', default=False, is_flag=True, show_default=True,
              help='Attach Python debugger when exceptions occur.')
@click.pass_context
def cli(ctx, debug_, log, pdb_):
    """
    The IFSbench command line utility.

    Specify one of the commands to see a usage description.
    \f

    This can be used to create hierarchical benchmark groups and thus achieve
    a similar appearance for nested commands, for example:

    .. code-block::

        from ifsbench import cli

        @cli.group()
        def t21():
            pass

        @t21.command('fc')
        def t21_fc():
            pass

        @t21.command('compo-fc')
        def t21_compo_fc():
            pass

    With this nesting the sub-commands will be available as

    .. code-block::

        <script-name> t21 fc
        <script-name> t21 compo-fc

    """
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj['DEBUG'] = debug_
    if debug_:
        logger.setLevel(DEBUG)
    if log:
        file_handler = FileHandler(log, mode='w')
        file_handler.setLevel(DEBUG)
        logger.addHandler(file_handler)
    if pdb_:
        sys.excepthook = auto_post_mortem_debugger


class RunOptions:
    """
    Storage object for run options that can be supplied to a command
    when using the :any:`run_options` decorator

    Parameters
    ----------
    nproc : int
        The total number of MPI ranks to use (default: 1)
    nthread : int
        The total number of threads to allocate for each rank (default: 1)
    hyperthread : int
        The number of hyperthreads to use per physical core (default: 1)
    nproc_io : int
        The number of dedicated IO-server ranks to use (default: 0)
    arch : str or None
        The name of the architecture :any:`Arch` in :any:`arch_registry` (default: None)
    launch_cmd : str or None
        A custom user-supplied launch command to use (default: None)
    launch_options : str or None
        Additional options ot pass to the launch command (default: None)
    forecast_length : str or None
        The length for which the forecast should be run (default: None)
    """

    def __init__(self, nproc=1, nthread=1, hyperthread=1, nproc_io=0,
                 arch=None, launch_cmd=None, launch_options=None,
                 forecast_length=None):

        self.nproc = nproc
        self.nthread = nthread
        self.hyperthread = hyperthread
        self.nproc_io = nproc_io
        self.arch = arch
        self.launch_cmd = launch_cmd
        self.launch_options = launch_options
        self.forecast_length = forecast_length


def run_options(func):
    """
    Decorator to add run-specific options to a benchmark sub-command

    This makes the following :any:`Benchmark.run` options available:

    * ``-n`` (``--nproc``): the total number of MPI ranks to use
    * ``-c`` (``--nthread``): the number of threads to allocate for each rank
    * ``--hyperthread``: the number of hyperthreads to use per physical core
    * ``--nproc-io``: the number of dedicated IO-server ranks to use
    * ``-a`` (``--arch``): the name of the :any:`Arch` description to use
      when looking up the architecture in the :any:`arch_registry`
    * ``-l`` (``--launch-cmd``): a custom launch command to use
    * ``--launch-options``: user-supplied options to pass to the launch
      command, e.g. accounting number, queue name, etc.
    * ``--fclen`` (``--forecast-length``): the time for which to run a forecast

    The options are stored in a :any:`RunOptions` object that is passed to
    the sub-command.

    To make these options available to a `click` command, simply apply the
    ``@run_options`` decorator:

    .. code-block::

        @cli.command('t21-fc')
        @run_options
        def t21_fc(runopts):
            print(f'Running with {runopts.nproc} ranks and {runopts.nthread} threads')
    """

    @click.option('-n', '--nproc', default=1, show_default=True, show_envvar=True,
                  help='Number of MPI processes to lauch')
    @click.option('-c', '--nthread', default=1, show_default=True, show_envvar=True,
                  help='Number of OpenMP threads to use')
    @click.option('--hyperthread', default=1, show_default=True, show_envvar=True,
                  help='Number of hyperthreads to use per physical core')
    @click.option('--nproc-io', default=0, show_default=True, show_envvar=True,
                  help='Number of dedicated IO-server ranks to use')
    @click.option('-a', '--arch', default=None, show_envvar=True,
                  help='Architecture name for specialized invocation')
    @click.option('-l', '--launch-cmd', default=None, show_envvar=True,
                  help='Custom launcher command to prepend to run')
    @click.option('--launch-options', default=None, show_envvar=True,
                  help='User options to add to the launch command (ignored if using --launch-cmd')
    @click.option('--forecast-length', '--fclen', default=None, show_envvar=True,
                  help='Length of forecast (e.g., h240 or d10)')
    @click.option('--nproma', default=None, help='Override the value of NPROMA')
    @click.pass_context
    @wraps(func)
    def process_run_options(ctx, *args, **kwargs):
        """
        Wrapper function to parse options into a utility object
        """
        runopts = ctx.ensure_object(RunOptions)
        runopts.nproc = kwargs.pop('nproc')
        runopts.nthread = kwargs.pop('nthread')
        runopts.hyperthread = kwargs.pop('hyperthread')
        runopts.nproc_io = kwargs.pop('nproc_io')
        runopts.arch = kwargs.pop('arch')
        runopts.launch_cmd = kwargs.pop('launch_cmd')
        runopts.launch_options = kwargs.pop('launch_options')
        runopts.forecast_length = kwargs.pop('forecast_length')
        runopts.nproma = kwargs.pop('nproma')
        return ctx.invoke(func, *args, runopts, **kwargs)

    return process_run_options


class ReferenceOptions:
    """
    Storage object for options related to validation and reference results
    that can be supplied to a command when using the :any:`reference_options` decorator

    Parameters
    ----------
    path : str
        The filepath of the reference record (default: None)
    validate : bool
        Flag to enable validation against reference (default: True)
    update : bool
        Flag to update reference record with result of the run (default: False)
    comment : str
        Comment to store with the reference record when updating reference (default: None)
    """

    def __init__(self, path=None, validate=True, update=False, comment=None):

        self.path = path
        self.validate = validate
        self.update = update
        self.comment = comment


def reference_options(func):
    """
    Decorator to add reference and validation options to a benchmark sub-command

    This makes the following options available:

    * ``-r`` (``--reference``): Path to custom reference record for validation
    * ``--validate``/``--no-validate``: Flag to enable or disable validation against reference
    * ``--update-reference``: Flag to update reference record with result
    * ``--comment``: Comment to store when updating reference record

    The options are stored in a :any:`ReferenceOptions` object that is passed to
    the sub-command.

    To make these options available to a `click` command, simply apply the
    ``@reference_options`` decorator:

    .. code-block::

        @cli.command('t21-fc')
        @reference_options
        def t21_fc(refopts):
            print(f'Validate against reference record in {refopts.path}')
    """

    @click.option('-r', '--reference', type=click.Path(), default=None, show_envvar=True,
                  help='Path to custom reference record for validation')
    @click.option('--validate/--no-validate', default=True, show_envvar=True,
                  help='Flag to enable validation against reference')
    @click.option('--update-reference', default=False, is_flag=True, show_envvar=True,
                  help='Flag to update reference record with result')
    @click.option('--comment', default=None, show_envvar=True,
                  help='Comment to store when updating reference record')
    @click.pass_context
    @wraps(func)
    def process_reference_options(ctx, *args, **kwargs):
        """
        Wrapper function to parse options into a utility object
        """
        refopts = ctx.ensure_object(ReferenceOptions)
        refopts.path = kwargs.pop('reference')
        refopts.validate = kwargs.pop('validate')
        refopts.update = kwargs.pop('update_reference')
        refopts.comment = kwargs.pop('comment')
        return ctx.invoke(func, *args, refopts, **kwargs)

    return process_reference_options
