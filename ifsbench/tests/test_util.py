# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for utility routines
"""

from pathlib import Path
import sys
import tempfile

from ifsbench.util import execute


def test_execute():
    """
    Test some aspects of the execute() utility.
    """
    # Very trivial executables with success/error exit codes
    assert execute('true').exit_code == 0
    assert execute('false').exit_code == 1

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        # basic logfile capture validation
        logfile = Path(tmp_dir) / 'test_execute.log'
        result = execute(['echo', 'foo', 'bar'], logfile=logfile)
        assert logfile.read_text() == 'foo bar\n'
        assert result.stdout == 'foo bar\n'

        # verify env
        execute(['env'], logfile=logfile, env={'FOO': 'bar', 'BAR': 'foo'})
        with logfile.open('r') as f:
            env_str = f.read()
            assert 'FOO=bar' in env_str
            assert 'BAR=foo' in env_str

        # no output executable
        execute(['true'], logfile=logfile)
        assert logfile.read_text() == ''

        # Output a lot of lines
        text = 'abc\n' * 100
        execute(['echo', text], logfile=logfile)
        assert logfile.read_text() == text + '\n'

        # Write to stderr
        result = execute(
            [sys.executable, '-c', "import sys; print('foo bar', file=sys.stderr)"], logfile=logfile
        )
        assert logfile.read_text() == 'foo bar\n'
        assert result.stdout == ''
        assert result.stderr == 'foo bar\n'


def test_execute_dryrun():
    """
    Test the execute function in dryrun mode..
    """
    # Very trivial executables with success/error exit codes
    assert execute('true', dryrun=True).exit_code == 0
    assert execute('false', dryrun=True).exit_code == 0

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        # basic logfile capture validation
        logfile = Path(tmp_dir) / 'test_execute.log'
        result = execute(['echo', 'foo', 'bar'], dryrun=True, logfile=logfile)
        assert not logfile.exists()
        assert result.stdout == ''
