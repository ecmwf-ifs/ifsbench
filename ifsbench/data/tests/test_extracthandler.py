# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for the ExtractHandler class.
"""

from contextlib import nullcontext
from pathlib import Path
import shutil

import pytest

from ifsbench.data import ExtractHandler


@pytest.mark.parametrize(
    'archive_path,archive_valid',
    [('somewhere/archive.tar', True), (None, False), (2, False)],
)
@pytest.mark.parametrize(
    'target_dir, target_valid',
    [('somewhere/archive.tar', True), (None, True), (2, False)],
)
def test_extracthandler_init(archive_path, archive_valid, target_dir, target_valid):
    """
    Initialise the ExtractHandler and make sure that only correct values are accepted.
    """
    if archive_valid and target_valid:
        context = nullcontext()
    else:
        context = pytest.raises(Exception)
    config = {'archive_path': archive_path}
    if target_dir:
        config['target_dir'] = target_dir

    with context:
        ExtractHandler.from_config(config)


@pytest.mark.parametrize(
    'target_dir',
    ['somewhere/archive.tar', None],
)
def test_extracthandler_model_dump(target_dir):
    """
    Initialise the ExtractHandler and make sure that only correct values are accepted.
    """
    archive_path = 'somewhere/archive.tar'

    config = {'archive_path': archive_path}
    if target_dir:
        config['target_dir'] = target_dir

    eh = ExtractHandler.from_config(config)
    config_dump = eh.dump_config()

    expected = dict(config)
    expected['handler_type'] = ExtractHandler.__name__
    assert config_dump == expected


@pytest.fixture(name='archive')
def fixture_archive():
    paths = [
        'data1/file1.txt',
        'data1/file2.txt',
        'data2/file1.txt',
        'data2/file2.txt',
    ]

    return paths


@pytest.mark.parametrize(
    'archive_path',
    [
        'somewhere/archive',
    ],
)
@pytest.mark.parametrize('archive_relative', [True, False])
@pytest.mark.parametrize('archive_type', ['zip', 'tar', 'gztar'])
@pytest.mark.parametrize(
    'target_dir',
    [
        'somewhere/extract',
        None,
    ],
)
@pytest.mark.parametrize('target_relative', [True, False])
def test_extracthandler_execute(
    tmp_path,
    archive,
    archive_path,
    archive_relative,
    archive_type,
    target_dir,
    target_relative,
):
    """
    Test that the execute function moves the content of an archive to the right
    directory.

        Parameters
        ----------
        tmp_path: `pathlib.Path`
            pytest-provided temporary directory which acts as our working directory.

        fixture_archive:
            Directory structure inside the archive.

        archive_path:
            Relative path (to tmp_path) where the archive resides, WITHOUT the
            archive suffix.

        archive_relative:
            Whether archive_path will be passed to the ExtractHandler as a relative
            or absolute path.

        archive_type:
            Which kind of archive is used (see `shutil.make_archive`).

        target_dir:
            Relative path (to tmp_path) where the data will be extracted to.

        target_relative:
            Whether target_dir will be passed to the ExtractHandler as a relative
            or absolute path.

    """
    # Build the paths that are passed to the ExtractHandler. If the paths
    # are supposed to be absolute, use tmp_path to build an absolute path.
    # Also distinguish between str and Path (ExtractHandler should support
    # both).
    if not archive_relative:
        if isinstance(archive_path, str):
            archive_path = str((tmp_path / archive_path).resolve())
        else:
            archive_path = (tmp_path / archive_path).resolve()

    if not target_relative and target_dir is not None:
        if isinstance(archive_path, str):
            target_dir = str((tmp_path / target_dir).resolve())
        else:
            target_dir = (tmp_path / target_dir).resolve()

    # Build the archive that we will unpack by using pack_path as a directory
    # that we will compress. Simply touch each file in fixture_archive.
    pack_path = tmp_path / 'pack'
    for path in archive:
        (pack_path / path).parent.mkdir(parents=True, exist_ok=True)
        (pack_path / path).touch()

    if Path(archive_path).is_absolute():
        archive_path = shutil.make_archive(archive_path, archive_type, pack_path)
    else:
        archive_path = shutil.make_archive(
            tmp_path / archive_path, archive_type, pack_path
        )

    # Actually extract the archive.
    config = {'archive_path': archive_path}
    if target_dir:
        config['target_dir'] = target_dir

    handler = ExtractHandler.from_config(config)
    handler.execute(tmp_path)

    # Build the path where the data should now be. As target_dir may be
    # a Path, str or None - and absolute or relative - we have to determine
    # the actual path first.
    if target_dir is None:
        extract_path = tmp_path
    else:
        extract_path = Path(target_dir)

    if not extract_path.is_absolute():
        extract_path = tmp_path / extract_path

    for path in archive:
        assert (extract_path / path).exists()
