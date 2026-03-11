# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests the Benchmark implementation.
"""

import logging
import re
import sys

import pytest

from ifsbench import (
    BenchmarkSetup,
    DefaultApplication,
    EnvHandler,
    EnvOperation,
    Job,
    MultiBenchmark,
    ScienceSetup,
)
from ifsbench.launch import Launcher, LaunchData


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


@pytest.fixture(name='benchmark_setup')
def fixture_benchmark_setup(tmp_path, request):
    setups = []

    env_handlers = [
        EnvHandler(mode=EnvOperation.CLEAR),
    ]
    job = Job(tasks=2)

    time_string = 'at t={time.time_ns() // 1_000_000}'
    for i in range(request.param):
        script_file = 'script_' + str(i) + '.py'
        script_path = tmp_path / script_file
        script_content = f"""
from pathlib import Path
import subprocess
import time

print(f'benchmark no. {i} sleeping {time_string}')
time.sleep(1)
print(f'benchmark no. {i} waking {time_string}')
Path('output.dat').touch()
"""
        with script_path.open('w') as f:
            f.write(script_content)

        science_application = DefaultApplication(
            command=[
                sys.executable,
                str(script_path),
            ]
        )

        science = ScienceSetup(
            application=science_application,
            env_handlers=env_handlers,
        )
        setups.append(BenchmarkSetup(science=science, job=job))
    return setups


@pytest.mark.parametrize('benchmark_setup', [3], indirect=['benchmark_setup'])
def test_multibenchmark_run(tmp_path, caplog, benchmark_setup):
    logging.getLogger('ifsbench').setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    setups = benchmark_setup
    mb = MultiBenchmark(setups=setups)
    stats = mb.run(run_dir=tmp_path, launcher=_DummyLauncher())
    start_times = {}
    end_times = {}
    for stat in stats:
        times = re.findall(r'\d+', stat.stdout)
        start_times[times[0]] = int(times[1])
        end_times[times[2]] = int(times[3])

        # Process execution should take longer than the 1s sleep time.
        assert stat.walltime > 1

    # The execution sleeps for 1 s;
    # the 2nd and 3rd benchmark are expected to start before the 1st one end
    # so their start times have to be considerably less than 1000 ms.
    assert start_times['1'] - start_times['0'] < 500
    assert start_times['2'] - start_times['0'] < 500
    assert end_times['0'] > start_times['1']
    assert end_times['0'] > start_times['2']

    # Check that the output directories are correctly numbered.
    for i in range(3):
        outfile = 'run_' + str(i)
        outpath = tmp_path / outfile
        assert (outpath / 'output.dat').exists()

    chunk_log = 'Running benchmarks in 1 set(s) of size 3'
    assert chunk_log in caplog.messages


@pytest.mark.parametrize('benchmark_setup', [3], indirect=['benchmark_setup'])
def test_multibenchmark_run_chunked(tmp_path, caplog, benchmark_setup):
    logging.getLogger('ifsbench').setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    setups = benchmark_setup
    mb = MultiBenchmark(setups=setups)

    stats = mb.run(run_dir=tmp_path, launcher=_DummyLauncher(), max_parallel=2)

    start_times = {}
    end_times = {}
    for stat in stats:
        times = re.findall(r'\d+', stat.stdout)
        start_times[times[0]] = int(times[1])
        end_times[times[2]] = int(times[3])

        # Process execution should take longer than the 1s sleep time.
        assert stat.walltime > 1

    # The execution sleeps for 1 s;
    # The 1st and 2nd benchmark run in parallel, the 3rd starts after those finish.
    assert start_times['1'] - start_times['0'] < 500
    assert start_times['2'] - start_times['0'] > 1000
    assert end_times['0'] > start_times['1']
    assert end_times['0'] < start_times['2']

    chunk_log = 'Running benchmarks in 2 set(s) of size 2'
    assert chunk_log in caplog.messages

    # Check that the output directories are correct independent of chunking.
    for i in range(3):
        outfile = 'run_' + str(i)
        outpath = tmp_path / outfile
        assert (outpath / 'output.dat').exists()


@pytest.mark.parametrize('benchmark_setup', [3], indirect=['benchmark_setup'])
def test_multibenchmark_run_chunked_single_chunk(tmp_path, caplog, benchmark_setup):
    logging.getLogger('ifsbench').setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    setups = benchmark_setup
    mb = MultiBenchmark(setups=setups)

    stats = mb.run(run_dir=tmp_path, launcher=_DummyLauncher(), max_parallel=3)

    start_times = {}
    end_times = {}
    for stat in stats:
        times = re.findall(r'\d+', stat.stdout)
        start_times[times[0]] = int(times[1])
        end_times[times[2]] = int(times[3])

        # Process execution should take longer than the 1s sleep time.
        assert stat.walltime > 1

    # The execution sleeps for 1 s; all benchmarks should run in a single chunk.
    assert start_times['1'] - start_times['0'] < 500
    assert start_times['2'] - start_times['0'] < 500
    assert end_times['0'] > start_times['1']
    assert end_times['0'] > start_times['2']

    chunk_log = 'Running benchmarks in 1 set(s) of size 3'
    assert chunk_log in caplog.messages


@pytest.mark.parametrize('benchmark_setup', [3], indirect=['benchmark_setup'])
def test_multibenchmark_run_invalid_max_parallel(tmp_path, benchmark_setup):

    setups = benchmark_setup
    mb = MultiBenchmark(setups=setups)

    with pytest.raises(RuntimeError) as exceptinfo:
        mb.run(run_dir=tmp_path, launcher=_DummyLauncher(), max_parallel=0)

    assert (
        'Invalid value for maximum value of parallel runs, must be larger 0, was max_parallel=0'
        in str(exceptinfo.value)
    )
