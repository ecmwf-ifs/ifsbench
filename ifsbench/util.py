# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Collection of utility routines
"""

import asyncio
from dataclasses import dataclass
from enum import auto, Enum
from io import StringIO
from os import environ, getcwd
from pathlib import Path
from pprint import pformat
import sys
from time import time
from typing import List

from ifsbench.logging import debug, info


__all__ = ['ExecuteResult', 'execute', 'execute_async', 'auto_post_mortem_debugger']


@dataclass
class ExecuteResult:
    """
    Results of an :func:`execute` invocation.
    """

    #: The captured standard output.
    stdout: str

    #: The captured standard error.
    stderr: str

    #: The return code of the execution.
    exit_code: int

    # Run time of the execution in [s].
    wall_time: int


def execute(command: List[str], **kwargs) -> ExecuteResult:
    """
    Execute a single command with a given directory or environment.

    Parameters
    ----------
    command : list of str
        The (components of the) command to execute.
    cwd : str, optional
        Directory in which to execute command.
    dryrun : bool, optional
        Do not actually run the command but log it (default: `False`).
    logfile : str, optional
        Write stdout to this file (default: `None`).

    Returns
    -------
    ExecuteResult:
        The results of the execution (stdout, stderr, exit code)
    """

    async def _async_task(command: List[str], **kwargs):
        task = asyncio.create_task(execute_async(command, **kwargs))
        result = await task
        return result

    return asyncio.run(_async_task(command, **kwargs))


async def execute_async(command: List[str], **kwargs) -> ExecuteResult:
    """
    Async execution of a single command with a given directory or environment.

    Parameters
    ----------
    command : list of str
        The (components of the) command to execute.
    cwd : str, optional
        Directory in which to execute command.
    dryrun : bool, optional
        Do not actually run the command but log it (default: `False`).
    logfile : str, optional
        Write stdout to this file (default: `None`).

    Returns
    -------
    ExecuteResult:
        The results of the execution (stdout, stderr, exit code)
    """
    start = time()

    cwd = kwargs.get('cwd', None)
    env = kwargs.get('env', None)
    dryrun = kwargs.pop('dryrun', False)
    logfile = kwargs.pop('logfile', None)

    debug(f'[ifsbench] User env:\n{pformat(env, indent=2)}')
    if env is not None:
        # Inject user-defined environment
        run_env = environ.copy()
        run_env.update(env)

        # Ensure all env variables are strings
        run_env = {k: str(v) for k, v in run_env.items()}
    else:
        run_env = None

    # Log the command we're about to execute
    cwd = getcwd() if cwd is None else str(cwd)
    debug('[ifsbench] Run directory: ' + cwd)
    info('[ifsbench] Executing: ' + ' '.join(command))

    if dryrun:
        # Only print the environment when in dryrun mode.
        info('[ifsbench] Environment: ' + str(run_env))
        wall_time = time() - start
        return ExecuteResult(stdout='', stderr='', exit_code=0, wall_time=wall_time)

    if logfile:
        # If we're file-logging, intercept via pipe
        _log_file = Path(logfile).open('w', encoding='utf-8')  # pylint: disable=consider-using-with
    else:
        _log_file = None

    stdout = StringIO()
    stderr = StringIO()

    class StreamType(Enum):
        STDOUT = auto()
        STDERR = auto()

    result_streams = {
        StreamType.STDOUT: (sys.stdout, stdout),
        StreamType.STDERR: (sys.stderr, stderr),
    }

    async def _read_and_multiplex(stream: asyncio.StreamReader, stream_type: StreamType):
        """
        Redirect output to both file and terminal
        """
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode()  # .strip()
            for st in result_streams[stream_type]:
                st.write(decoded)

            if logfile:
                # Also flush to logfile
                _log_file.write(decoded)
                _log_file.flush()

    # Execute with our args and outside args
    proc = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **kwargs
    )

    task_out = asyncio.create_task(_read_and_multiplex(proc.stdout, StreamType.STDOUT))
    task_err = asyncio.create_task(_read_and_multiplex(proc.stderr, StreamType.STDERR))
    await proc.wait()
    await task_out
    await task_err
    if _log_file:
        _log_file.close()

    wall_time = time() - start
    return ExecuteResult(
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        exit_code=proc.returncode,
        wall_time=wall_time,
    )


def as_tuple(item, dtype=None, length=None):
    """
    Force item to a tuple, even if `None` is provided.
    """
    # Stop complaints about `type` in this function
    # pylint: disable=redefined-builtin

    # Empty list if we get passed None
    if item is None:
        t = ()
    elif isinstance(item, str):
        t = (item,)
    else:
        # Convert iterable to list...
        try:
            t = tuple(item)
        # ... or create a list of a single item
        except (TypeError, NotImplementedError):
            t = (item,) * (length or 1)
    if length and not len(t) == length:
        raise ValueError(f'Tuple needs to be of length {length: d}')
    if dtype and not all(isinstance(i, dtype) for i in t):
        raise TypeError(f'Items need to be of type {dtype}')
    return t


def auto_post_mortem_debugger(type, value, tb):  # pylint: disable=redefined-builtin
    """
    Exception hook that automatically attaches a debugger

    Activate by setting ``sys.excepthook = auto_post_mortem_debugger``

    Adapted from
    https://code.activestate.com/recipes/65287-automatically-start-the-debugger-on-an-exception/
    """
    is_interactive = hasattr(sys, 'ps1')
    no_tty = not sys.stderr.isatty() or not sys.stdin.isatty() or not sys.stdout.isatty()
    if is_interactive or no_tty or type == SyntaxError:
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback  # pylint: disable=import-outside-toplevel
        import pdb  # pylint: disable=import-outside-toplevel

        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        # ...then start the debugger in post-mortem mode.
        pdb.post_mortem(tb)  # pylint: disable=no-member
