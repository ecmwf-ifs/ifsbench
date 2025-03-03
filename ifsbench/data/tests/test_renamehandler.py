# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for all classes that represent benchmark files
"""

import re

import pytest

from ifsbench.data import (
    RenameHandler, RenameMode
)

@pytest.mark.parametrize('pattern,repl,mode,files_in,files_out', [
    (r'file', 'data', RenameMode.MOVE,
        ['data/data.txt','data1/data1.txt'],
        ['data/data.txt','data1/data1.txt'],
    ),
    (r'(?P<name>data[^/]*.txt)', r'new_dir/\g<name>', RenameMode.COPY,
        ['data/data.txt','data1/data1.txt'],
        ['data/data.txt','data1/new_dir/data1.txt', 'data/data.txt','data1/new_dir/data1.txt'],
    ),
    (r'data[^/]*/', '', RenameMode.SYMLINK,
        ['data/data.txt','data1/data1.txt', 'data2/data1.txt'],
        None,
    ),
    (re.compile(r'(?P<name>data[^/]*.txt)'), r'newdir/\g<name>', RenameMode.SYMLINK,
        ['data/data.txt','data1/data1.txt', 'data2/data1.txt'],
        ['data/data.txt','data1/data1.txt', 'data2/data1.txt',
            'data/newdir/data.txt','data1/newdir/data1.txt',
            'data2/newdir/data1.txt'],
    ),
    (r'data[^/]*/', '', RenameMode.MOVE,
        ['data/data.txt','data1/data1.txt', 'data1/data2.txt'],
        ['data.txt', 'data1.txt', 'data2.txt'],
    ),
    (r'data[12]/', 'data/', RenameMode.MOVE,
        ['data/data.txt','data1/data.txt', 'data1/data2.txt'],
        ['data/data.txt', 'data/data2.txt'],
    ),
    (re.compile(r'replacement$'), 'dummypath', RenameMode.COPY,
        ['dummypath/somedata.tar.gz','replacement'],
        ['dummypath', 'replacement'],
    ),
])
def test_renamehandler_from_filename(tmp_path, pattern, repl, mode, files_in, files_out):
    """
    Test that a RenameHandler created via from_filename works correctly.

        Parameters
        ----------
        tmp_path: `pathlib.Path`
            pytest-provided temporary directory which acts as our working directory.

        pattern:
            The filename pattern that is used.

        repl:
            The replacement pattern that is passed to from_filename

        mode:
            The renaming mode that is passed to from_filename.

        files_in:
            List of files that are initially placed in the working directory.

        files_out:
            List of files that are expected to be in the working directory after
            executing the RenameHandler.
            If files_out is None, the tests expects the execute command to fail.

    """
    handler = RenameHandler(pattern, repl, mode)

    # Create the initial files in the working directory.
    for f in files_in:
        (tmp_path/f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path/f).touch()

    if files_out is None:
        with pytest.raises(Exception):
            handler.execute(tmp_path)
        return

    handler.execute(tmp_path)

    # Count the number of files in the working directory and make sure that
    # this number is equal to len(file_out)
    n_out = len([f for f in tmp_path.rglob('*') if not f.is_dir()])
    assert n_out == len(files_out)

    for f in files_out:
        assert (tmp_path/f).exists()
