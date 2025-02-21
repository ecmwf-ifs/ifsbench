# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Collection of utility routines
"""
import contextlib
from os import environ, getcwd
from pathlib import Path
from pprint import pformat
import shutil
from subprocess import Popen, STDOUT, PIPE, CalledProcessError
import sys
import timeit

from ifsbench.logging import debug, info, warning, error


__all__ = [
    'execute', 'symlink_data', 'copy_data', 'Timer', 'classproperty',
    'auto_post_mortem_debugger'
]


def execute(command, **kwargs):
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
    stdout : optional
        Overwrite `stdout` attribute of :any:`subprocess.run`. Ignored if
        :attr:`logfile` is given (default: `None`).
    stderr : optional
        Overwrite `stderr` attribute of :any:`subprocess.run` (default: `None`).
    """
    cwd = kwargs.pop('cwd', None)
    env = kwargs.pop('env', None)
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

    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', STDOUT)

    # Log the command we're about to execute
    cwd = getcwd() if cwd is None else str(cwd)
    debug('[ifsbench] Run directory: ' + cwd)
    info('[ifsbench] Executing: ' + ' '.join(command))

    if dryrun:
        # Only print the environment when in dryrun mode.
        info('[ifsbench] Environment: ' + str(run_env))
        return

    cmd_args = {
        'cwd': cwd, 'env': run_env, 'text': True, 'stderr': stderr
    }

    if logfile:
        # If we're file-logging, intercept via pipe
        _log_file = Path(logfile).open('w', encoding='utf-8') # pylint: disable=consider-using-with
        cmd_args['stdout'] = PIPE
    else:
        _log_file = None
        cmd_args['stdout'] = stdout


    def _read_and_multiplex(p):
        """
        Read from ``p.stdout.read()`` and write to log and sys.stdout.
        """
        line = p.stdout.read()
        if line:
            # Forward to user output
            sys.stdout.write(line)

            # Also flush to logfile
            _log_file.write(line)
            _log_file.flush()

    try:
        # Execute with our args and outside args
        with Popen(command, **cmd_args, **kwargs) as p:

            if logfile:
                # Intercept p.stdout and multiplex to file and sys.stdout
                while p.poll() is None:
                    _read_and_multiplex(p)

            # Check for successful completion
            ret = p.wait()

            if logfile:
                # Read one last time to catch racy process output
                _read_and_multiplex(p)

        if ret:
            raise CalledProcessError(ret, command)

    except CalledProcessError as excinfo:
        error(f'Execution failed with return code: {excinfo.returncode}')
        raise excinfo

    finally:
        if _log_file:
            _log_file.close()


def symlink_data(source, dest, force=True):
    """
    Utility to symlink input data if it doesn't exist.

    :param source: Path of the original file to link to
    :param dest: Path of the new symlink
    :param force: Force delete and re-link for existing symlinks
    """
    if not source.exists():
        warning(f'Trying to link non-existent file: {source}')

    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    if dest.exists():
        if not dest.resolve() == source and force:
            # Delete and re-link of path points somewhere else
            dest.unlink()
            debug(f'Symlinking {source} -> {dest}')
            dest.symlink_to(source)
    else:
        debug(f'Symlinking {source} -> {dest}')
        dest.symlink_to(source)


def copy_data(source, dest, force=False):
    """
    Utility to copy input data if it doesn't exist.

    Note, if the target file exists, the "last modified" time will be
    used to decide if the file should be copoed iver again, unless the
    copy is explicitly forced.

    :param source: Path of the input file to copy
    :param dest: Path of the target to copy :param source: to
    :param force: Force delete and copy for existing symlinks
    """
    if not source.exists():
        raise RuntimeError(f'Trying to copy non-existent file: {source}')

    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    if dest.exists():
        if force or source.stat().st_mtime > dest.stat().st_mtime:
            # Delete and re-link if `dest` points somewhere else
            dest.unlink()
            debug(f'Copying {source} -> {dest}')
            shutil.copyfile(source, dest)
    else:
        debug(f'Copying {source} -> {dest}')
        shutil.copyfile(source, dest)


@contextlib.contextmanager
def Timer(name=None):
    """
    Utility to do inline timing of code blocks
    """
    start_time = timeit.default_timer()
    yield
    end_time = timeit.default_timer()
    time = end_time - start_time
    print(f'Timer::{name}: {time:.3f} s')


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


def is_iterable(o):
    """
    Checks if an item is truly iterable using duck typing.

    This was added because :class:`pymbolic.primitives.Expression` provide an ``__iter__`` method
    that throws an exception to avoid being iterable. However, with that method defined it is
    identified as a :class:`collections.Iterable` and thus this is a much more reliable test.
    """
    try:
        iter(o)
    except TypeError:
        return False
    return True


def flatten(l):
    """
    Flatten a hierarchy of nested lists into a plain list.
    """
    newlist = []
    for el in l:
        if is_iterable(el) and not isinstance(el, (str, bytes)):
            for sub in flatten(el):
                newlist.append(sub)
        else:
            newlist.append(el)
    return newlist


class classproperty:
    """
    Decorator to make classmethods available as class properties
    """

    def __init__(self, method):
        self._method = method

    def __get__(self, instance, owner):  # pylint:disable=unused-argument
        return self._method(owner)


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
        import traceback # pylint: disable=import-outside-toplevel
        import pdb # pylint: disable=import-outside-toplevel
        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        # ...then start the debugger in post-mortem mode.
        pdb.post_mortem(tb)   # pylint: disable=no-member
