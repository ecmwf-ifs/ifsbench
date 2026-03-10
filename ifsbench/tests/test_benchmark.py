# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests the Benchmark implementation.
"""

from pathlib import Path
from typing import List
from time import sleep
import sys
import yaml

import pytest
from typing_extensions import Literal

from ifsbench import (
    Benchmark,
    BenchmarkSetup,
    ScienceSetup,
    TechSetup,
    DefaultApplication,
    EnvOperation,
    EnvHandler,
    CpuConfiguration,
    Job,
    DefaultArch,
)
from ifsbench.data import DataHandler
from ifsbench.launch import Launcher, LaunchData


@pytest.fixture(name='test_setup_files')
def fixture_test_setup_files():
    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]

    class TouchHandler(DataHandler):
        handler_type: Literal['TouchHandler'] = 'TouchHandler'
        path: str

        def execute(self, wdir, **kwargs):
            (wdir / self.path).touch()

    data_handlers = [
        TouchHandler(path='file1'),
        TouchHandler(path='file2'),
    ]

    science_files = [Path('file1'), Path('file2')]

    science = ScienceSetup(
        application={'class_name': 'DefaultApplication', 'command': ['pwd']},
        env_handlers=env_handlers,
        data_handlers_init=data_handlers,
    )

    tech = TechSetup(data_handlers_init=[TouchHandler(path='file3')])

    tech_files = [Path('file3')]

    # Return example tech and science setup as well as the list of files that should
    # be created by the science/tech data handles.
    return science, tech, science_files, tech_files


@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('use_tech', [True, False])
def test_defaultbenchmark_setup_rundir(tmp_path, test_setup_files, force, use_tech):
    """
    Test the Benchmark.setup_rundir function.
    """

    science, tech, science_list, tech_list = test_setup_files
    job = Job(tasks=2)

    if use_tech:
        setup = BenchmarkSetup(science=science, job=job, tech=tech)
    else:
        setup = BenchmarkSetup(science=science, job=job)
    benchmark = Benchmark(setup=setup)

    # Create the run directory and check that all files in file list
    # actually exist.
    benchmark.setup_rundir(tmp_path, force)

    file_list = science_list
    if use_tech:
        file_list += tech_list

    for file in file_list:
        assert (tmp_path / file).exists()

    # We test the "force" flag now. First, we store the current
    # "access time" attributes for all the files and sleep.
    stats = {file: (tmp_path / file).stat() for file in file_list}

    sleep(1e-1)

    # Now we rerun the setup and check afterwards, if the access times have
    # changed. This gives us information on whether or not the files have been
    # updated.
    benchmark.setup_rundir(tmp_path, force)
    for file in file_list:
        stat = (tmp_path / file).stat()

        # If force was used, the files should have been updated.
        if force:
            assert stat.st_atime != stats[file].st_atime
        else:
            assert stat.st_atime == stats[file].st_atime


class DummyApplication(DefaultApplication):
    def get_command(self, run_dir: Path, job: Job) -> List[str]:
        job_config = job.dump_config()

        command = [
            sys.executable,
            '-c',
            'from pathlib import Path; import yaml; '
            f'f = open("{self.command[0]}", "w"); '
            f'yaml.dump({job_config}, f); '
            'f.close()',
        ]
        return command


@pytest.fixture(name='tech_setup_application')
def fixture_tech_setup_application(request):
    tech_application = None
    if request.param:
        tech_application = DummyApplication(command=['tech.txt'])

    tech = TechSetup(
        application=tech_application,
        env_handlers=[EnvHandler(mode=EnvOperation.SET, key='KEY', value='VALUE')],
    )

    return tech


@pytest.fixture(name='test_run_science_setup')
def fixture_test_run_science_setup():
    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]

    science_application = DummyApplication(command=['science.txt'])

    science = ScienceSetup(
        application=science_application,
        env_handlers=env_handlers,
    )

    return science


class _DummyLauncher(Launcher):
    """
    Dummy launcher that just calls the given executable.
    """

    _prepare_called = False

    def prepare(
        self,
        run_dir,
        job,
        cmd,
        library_paths=None,
        env_pipeline=None,
        custom_flags=None,
    ):
        self._prepare_called = True
        return LaunchData(run_dir=run_dir, cmd=cmd)


@pytest.mark.parametrize('job_override', [None, Job(tasks=2, account='override')])
@pytest.mark.parametrize('use_arch', [False, True])
@pytest.mark.parametrize(
    'use_launcher, launcher_flags',
    [(False, None), (True, None), (True, ['something'])],
)
@pytest.mark.parametrize(
    'use_tech, tech_setup_application',
    [(True, True), (True, False), (False, False)],
    indirect=['tech_setup_application'],
)
def test_defaultbenchmark_run(
    tmp_path,
    test_run_science_setup,
    job_override,
    use_arch,
    use_launcher,
    launcher_flags,
    use_tech,
    tech_setup_application,
):
    """
    Test the Benchmark.run function.
    """

    launcher = _DummyLauncher() if use_launcher else None
    arch = (
        DefaultArch.from_config(
            {
                'launcher': {'class_name': '_DummyLauncher'},
                'cpu_config': CpuConfiguration(),
            }
        )
        if use_arch
        else None
    )

    science = test_run_science_setup
    tech = tech_setup_application
    job = Job(tasks=5, account='default')

    if use_tech:
        setup = BenchmarkSetup(science=science, job=job, tech=tech)
    else:
        setup = BenchmarkSetup(science=science, job=job)
    benchmark = Benchmark(setup=setup)

    if arch is None and launcher is None:
        with pytest.raises(ValueError):
            benchmark.run(tmp_path, job_override, arch, launcher, launcher_flags)
        return

    result = benchmark.run(tmp_path, job_override, arch, launcher, launcher_flags)
    assert result.walltime > 0

    if launcher is not None:
        assert launcher._prepare_called is True
        if arch is not None:
            assert arch.get_default_launcher()._prepare_called is False
    elif arch is not None:
        assert arch.get_default_launcher()._prepare_called is True

    # Confirm the correct application was run, ScienceSetup vs TechSetup
    out_file = 'tech.txt' if tech.application else 'science.txt'
    output_path = tmp_path / out_file
    assert (output_path).exists()

    # Confirm the correct job was run, the benchmark member or the override
    with output_path.open('r') as f:
        config = yaml.safe_load(f)
    executed_job = Job.from_config(config)
    if job_override:
        assert executed_job == job_override
    else:
        assert executed_job == job
