# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for the RenameHandler class.
"""

import pytest

from ifsbench.data import RenameHandler, RenameMode


@pytest.mark.parametrize(
    'pattern,repl,mode',
    [
        (
            r'file',
            'data',
            RenameMode.MOVE,
        ),
        (
            r'data[^/]*/',
            '',
            RenameMode.SYMLINK,
        ),
    ],
)
def test_renamehandler_from_config_dump_config(pattern, repl, mode):
    config_in = {'pattern': pattern, 'repl': repl, 'mode': mode}

    rh = RenameHandler.from_config(config_in)

    config_out = rh.dump_config()

    expected = dict(config_in)
    assert config_out == expected


@pytest.mark.parametrize(
    'pattern,repl,mode,files_in,files_out',
    [
        (
            r'file',
            'data',
            RenameMode.MOVE,
            ['data/data.txt', 'data1/data1.txt'],
            ['data/data.txt', 'data1/data1.txt'],
        ),
        (
            r'(?P<name>data[^/]*.txt)',
            r'new_dir/\g<name>',
            RenameMode.COPY,
            ['data/data.txt', 'data1/data1.txt'],
            [
                'data/data.txt',
                'data1/new_dir/data1.txt',
                'data/data.txt',
                'data1/new_dir/data1.txt',
            ],
        ),
        (
            r'data[^/]*/',
            '',
            RenameMode.SYMLINK,
            ['data/data.txt', 'data1/data1.txt', 'data2/data1.txt'],
            None,
        ),
        (
            r'(?P<name>data[^/]*.txt)',
            r'newdir/\g<name>',
            RenameMode.SYMLINK,
            ['data/data.txt', 'data1/data1.txt', 'data2/data1.txt'],
            [
                'data/data.txt',
                'data1/data1.txt',
                'data2/data1.txt',
                'data/newdir/data.txt',
                'data1/newdir/data1.txt',
                'data2/newdir/data1.txt',
            ],
        ),
        (
            r'data[^/]*/',
            '',
            RenameMode.MOVE,
            ['data/data.txt', 'data1/data1.txt', 'data1/data2.txt'],
            ['data.txt', 'data1.txt', 'data2.txt'],
        ),
        (
            r'data[12]/',
            'data/',
            RenameMode.MOVE,
            ['data/data.txt', 'data1/data.txt', 'data1/data2.txt'],
            ['data/data.txt', 'data/data2.txt'],
        ),
        (
            r'replacement$',
            'dummypath',
            RenameMode.COPY,
            ['dummypath/somedata.tar.gz', 'replacement'],
            ['dummypath', 'replacement'],
        ),
    ],
)
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
    handler = RenameHandler(pattern=pattern, repl=repl, mode=mode)

    # Create the initial files in the working directory.
    for f in files_in:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).touch()

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
        assert (tmp_path / f).exists()


def test_renamehandler_symlink(tmp_path):
    """
    Test that a RenameHandler deals with symlinks correctly.
    """

    (tmp_path / 'subdir').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'subdir/file.txt').touch()
    (tmp_path / 'subdir/symlink').symlink_to(tmp_path / 'subdir/file.txt')

    handler = RenameHandler(pattern='file', repl='dir', mode=RenameMode.SYMLINK)

    handler.execute(tmp_path)

    assert (tmp_path / 'subdir/dir.txt').exists()
    assert (tmp_path / 'subdir/file.txt').exists()
    assert (tmp_path / 'subdir/symlink').exists()

    assert (tmp_path / 'subdir/symlink').resolve() == tmp_path / 'subdir/file.txt'
