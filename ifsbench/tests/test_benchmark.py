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

from ifsbench import (DefaultBenchmark, DefaultScienceSetup, DefaultTechSetup,
                      DefaultApplication, EnvOperation, EnvHandler,
                      CpuConfiguration, Job, DefaultArch)
from ifsbench.data import DataHandler
from ifsbench.launch import Launcher, LaunchData


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

    science_files = [Path('file1'), Path('file2')]

    science = DefaultScienceSetup(
        application=DefaultApplication(command=['pwd']),
        env_handlers=env_handlers,
        data_handlers_init=data_handlers
    )

    tech = DefaultTechSetup(
        data_handlers_init = [TouchHandler(path='file3')]
    )

    tech_files = [Path('file3')]

    # Return example tech and science setup as well as the list of files that should
    # be created by the science/tech data handles.
    return science, tech, science_files, tech_files


@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('use_tech', [True, False])
def test_defaultbenchmark_setup_rundir(tmp_path, test_setup_files, force, use_tech):
    """
    Test the DefaultBenchmark.setup_rundir function.
    """

    science, tech, science_list, tech_list = test_setup_files

    if use_tech:
        benchmark = DefaultBenchmark(science=science, tech=tech)
    else:
        benchmark = DefaultBenchmark(science=science)

    # Create the run directory and check that all files in file list
    # actually exist.
    benchmark.setup_rundir(tmp_path, force)

    file_list = science_list
    if use_tech:
        file_list += tech_list

    for file in file_list:
        assert (tmp_path/file).exists()

    # We test the "force" flag now. First, we store the current
    # "access time" attributes for all the files and sleep.
    stats = {file: (tmp_path/file).stat() for file in file_list}

    sleep(1e-1)

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

    science = DefaultScienceSetup(
        application = application,
        env_handlers = env_handlers,
    )

    tech = DefaultTechSetup(
        env_handlers = [EnvHandler(mode=EnvOperation.SET, key='KEY', value='VALUE')]
    )

    return science, tech

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
@pytest.mark.parametrize('use_tech', [True, False])
def test_defaultbenchmark_run(tmp_path, test_run_setup, job, arch, launcher, launcher_flags, use_tech):
    """
    Test the DefaultBenchmark.run function.
    """

    science, tech = test_run_setup

    if use_tech:
        benchmark = DefaultBenchmark(science=science, tech=tech)

    else:
        benchmark = DefaultBenchmark(science=science)

    # Create the run directory and check that all files in file list
    # actually exist.
    benchmark.setup_rundir(tmp_path)

    if arch is None and launcher is None:
        with pytest.raises(ValueError):
            benchmark.run(tmp_path, job, arch, launcher, launcher_flags)
        return

    benchmark.run(tmp_path, job, arch, launcher, launcher_flags)

    assert (tmp_path/'test.txt').exists()
