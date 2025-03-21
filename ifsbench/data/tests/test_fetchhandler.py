# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for the FetchHandler class.
"""

from pathlib import Path

import pytest

from ifsbench.data import FetchHandler


@pytest.mark.parametrize('source_url', ['file://home/some_file.tar.gz'])
@pytest.mark.parametrize('target_path', [Path('subdir/target.tar.gz')])
@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('ignore_errors', [True, False])
def test_fetchhandler_serialise(source_url, target_path, force, ignore_errors):
    """
    Serialise and deserialise a FetchHandler and make sure the the resulting
    object is correct.
    """
    config = {
        'source_url': source_url, 
        'target_path': target_path,
        'force': force,
        'ignore_errors': ignore_errors
    }

    handler = FetchHandler(**config)

    config_dump = handler.dump_config()
    new_handler = FetchHandler.from_config(config_dump)

    assert new_handler.source_url == source_url
    assert new_handler.target_path == target_path
    assert new_handler.force == force
    assert new_handler.ignore_errors == ignore_errors

@pytest.fixture(name='run_dir')
def fixture_rundir(tmp_path):
    """
    Create temporary directory with two files.
    """
    with (tmp_path/'hello.txt').open('w') as f:
        f.write("Hello!")
    with (tmp_path/'goodbye.txt').open('w') as f:
        f.write("Goodbye!")

    return tmp_path

@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('ignore_errors', [True, False])
def test_fetchhandler_force(run_dir, force, ignore_errors):
    """
    Check that the force flag is working as intended.    
    """

    # Essentially replace goodbye.txt with hello.txt. If force is False,
    # the original goodbye.txt file should remain, otherwise it should
    # have the same content as hello.txt.

    handler = FetchHandler(
        source_url=f"file://{run_dir}/hello.txt",
        target_path=run_dir/'goodbye.txt',
        force=force,
        ignore_errors=ignore_errors
    )

    handler.execute(run_dir)

    with (run_dir/'goodbye.txt').open('r') as f:
        result = f.read()

    if force:
        assert result == 'Hello!'
    else:
        assert result == 'Goodbye!'

@pytest.mark.parametrize('ignore_errors', [True, False])
def test_fetchhandler_ignore_errors(run_dir, ignore_errors):
    """
    Check that the ignore_errors flag works as intended by trying to fetch
    a non-existent file.
    """
    handler = FetchHandler(
        source_url=f"file://{run_dir}/non_existent.txt",
        target_path=run_dir/'goodbye.txt',
        force=True,
        ignore_errors=ignore_errors
    )

    if ignore_errors:
        handler.execute(run_dir)
    else:
        with pytest.raises(RuntimeError):
            handler.execute(run_dir)

@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('ignore_errors', [True, False])
def test_fetchhandler_path_handling(run_dir, force, ignore_errors):
    """
    Test the relative/absolute path handling in the FetchHandler.
    """

    handler = FetchHandler(
        source_url=f"file://{run_dir}/hello.txt",
        target_path=run_dir/'subdir/new_file.txt',
        force=force,
        ignore_errors=ignore_errors
    )

    handler.execute(run_dir)

    assert (run_dir/'subdir/new_file.txt').exists()

    handler.target_path=Path('subdir/another_new_file.txt')

    handler.execute(run_dir)

    assert (run_dir/'subdir/another_new_file.txt').exists()
