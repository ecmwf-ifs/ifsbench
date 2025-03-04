# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests the DefaultBenchmark implementation.
"""

from pathlib import Path
from time import sleep
import sys

import pytest

from ifsbench import (DefaultBenchmark, DefaultBenchmarkSetup, DefaultApplication,
                      EnvOperation, EnvHandler, CpuConfiguration, Job, DefaultArch)
from ifsbench.data import ExtractHandler, DataHandler
from ifsbench.launch import Launcher, LaunchData


@pytest.fixture(name='test_setup_empty')
def fixture_test_setup_empty():
    return DefaultBenchmarkSetup()

@pytest.fixture(name='test_setup_1')
def fixture_test_setup_1():
    env_handlers = [
        EnvHandler(mode=EnvOperation.SET, key='SOMEVALUE', value='2'),
        EnvHandler(mode=EnvOperation.APPEND, key='SOMELIST', value='1'),
    ]

    data_handlers = [
        ExtractHandler(archive_path='some_path.tar.gz')
    ]

    return DefaultBenchmarkSetup(
        application = DefaultApplication(command=['ls', '-l']),
        env_handlers = env_handlers,
        data_handlers = data_handlers
    )

@pytest.fixture(name='test_setup_2')
def fixture_test_setup_2():
    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]

    data_handlers = [
        ExtractHandler(archive_path='some_path.tar.gz'),
        ExtractHandler(archive_path='some_other_path.tar.gz'),
    ]

    return DefaultBenchmarkSetup(
        application = DefaultApplication(command=['pwd']),
        env_handlers = env_handlers,
        data_handlers = data_handlers
    )

@pytest.mark.parametrize('name1', ['test_setup_empty', 'test_setup_1', 'test_setup_1'])
@pytest.mark.parametrize('name2', ['test_setup_empty', 'test_setup_1', 'test_setup_1'])
def test_defaultbenchmark_setup_merge(request, name1, name2):
    """
    Test the DefaultBenchmarkSetup.merge function.
    """
    setup1 = request.getfixturevalue(name1)
    setup2 = request.getfixturevalue(name2)

    setup_merge = setup1.merge(setup2)

    assert len(setup_merge.data_handlers) == len(setup1.data_handlers + setup2.data_handlers)
    assert len(setup_merge.env_handlers) == len(setup1.env_handlers + setup2.env_handlers)

    if setup2.application is None:
        assert setup_merge.application == setup1.application
    else:
        assert setup_merge.application == setup2.application

@pytest.fixture(name='test_setup_files')
def fixture_test_setup_files():
    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]

    class TouchHandler(DataHandler):
        def __init__(self, path):
            self.path = path

        def execute(self, wdir, **kwargs):
            (wdir/self.path).touch()

    data_handlers = [
        TouchHandler(path='file1'),
        TouchHandler(path='file2'),
    ]

    file_list = [Path('file1'), Path('file2')]

    return DefaultBenchmarkSetup(
        application = DefaultApplication(command=['pwd']),
        env_handlers = env_handlers,
        data_handlers = data_handlers
    ), file_list

@pytest.mark.parametrize('force', [True, False])
def test_defaultbenchmark_setup_rundir(tmp_path, test_setup_files, force):
    """
    Test the DefaultBenchmark.setup_rundir function.
    """

    setup = test_setup_files[0]
    file_list = test_setup_files[1]

    benchmark = DefaultBenchmark(setup=setup)

    # Create the run directory and check that all files in file list
    # actually exist.
    benchmark.setup_rundir(tmp_path, force)

    for file in file_list:
        assert (tmp_path/file).exists()

    # We test the "force" flag now. First, we store the current
    # "access time" attributes for all the files and sleep.
    stats = {file: (tmp_path/file).stat() for file in file_list}

    sleep(1e-2)

    # Now we rerun the setup and check afterwards, if the access times have
    # changed. This gives us information on whether or not the files have been
    # updated.
    benchmark.setup_rundir(tmp_path, force)
    for file in file_list:
        stat = (tmp_path/file).stat()

        # If force was used, the files should have been updated.
        if force:
            assert stat.st_atime != stats[file].st_atime
        else:
            assert stat.st_atime == stats[file].st_atime


@pytest.fixture(name='test_run_setup')
def fixture_test_run_setup():
    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]

    application = DefaultApplication(
        command = [sys.executable, '-c', 'from pathlib import Path; Path(\'test.txt\').touch()']
    )

    return DefaultBenchmarkSetup(
        application = application,
        env_handlers = env_handlers,
    )

class _DummyLauncher(Launcher):
    """
    Dummy launcher that just calls the given executable.
    """
    def prepare(self, run_dir, job, cmd, library_paths=None, env_pipeline=None, custom_flags=None):
        return LaunchData(run_dir=run_dir, cmd=cmd)


@pytest.mark.parametrize('job', [Job(tasks=2)])
@pytest.mark.parametrize('arch', [None, DefaultArch(_DummyLauncher(), CpuConfiguration())])
@pytest.mark.parametrize('launcher, launcher_flags', [
    (None, None),
    (_DummyLauncher(), None),
    (_DummyLauncher(), ['something'])
])
def test_defaultbenchmark_run(tmp_path, test_run_setup, job, arch, launcher, launcher_flags):
    """
    Test the DefaultBenchmark.run function.
    """

    benchmark = DefaultBenchmark(setup=test_run_setup)

    # Create the run directory and check that all files in file list
    # actually exist.
    benchmark.setup_rundir(tmp_path)

    if arch is None and launcher is None:
        with pytest.raises(ValueError):
            benchmark.run(tmp_path, job, arch, launcher, launcher_flags)
        return

    benchmark.run(tmp_path, job, arch, launcher, launcher_flags)

    assert (tmp_path/'test.txt').exists()
