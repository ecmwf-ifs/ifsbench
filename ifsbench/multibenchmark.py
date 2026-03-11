# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Implementation for running multiple benchmarks in parallel.
"""

import asyncio
from pathlib import Path
from typing import List, Optional


from ifsbench.arch import Arch
from ifsbench.benchmark import Benchmark, BenchmarkSetup, BenchmarkSummary
from ifsbench.job import Job
from ifsbench.launch import Launcher
from ifsbench.serialisation_mixin import SerialisationMixin


__all__ = ['MultiBenchmark']


SUBDIRECTORY_PREFIX = 'run_'


class MultiBenchmark(SerialisationMixin):
    """
    Run several benchmarks asynchronously.

    Each benchmark is defined by one BenchmarkSetup;
    the output will be in subdirectories of the specified
    run directory, named 'run_<number>'.
    """

    setups: List[BenchmarkSetup]

    def _sub_run_dir(self, run_dir: Path, run_number: int) -> Path:
        sub_dir = SUBDIRECTORY_PREFIX + str(run_number)
        return run_dir / sub_dir

    async def _run_async(
        self, run_dir, job, arch, launcher, launcher_flags, benchmarks: List[Benchmark]
    ) -> List[BenchmarkSummary]:

        run_dir.mkdir(parents=True, exist_ok=True)

        tasks = [
            asyncio.create_task(
                benchmark.run_async(
                    self._sub_run_dir(run_dir, i), job, arch, launcher, launcher_flags
                )
            )
            for i, benchmark in enumerate(benchmarks)
        ]
        return await asyncio.gather(*tasks)

    def run(
        self,
        run_dir: Path,
        job: Optional[Job] = None,
        arch: Optional[Arch] = None,
        launcher: Optional[Launcher] = None,
        launcher_flags: Optional[List[str]] = None,
    ) -> List[BenchmarkSummary]:
        """
        Run the benchmark.

        Parameters
        ----------
        run_dir: pathlib.Path
            The path to the base run directory, the individual runs will be in subdirectories.
        job: Job
            The parallel setup for the benchmark. If None, the Job from the BenchmarkSetup is used.
        arch: Arch
            A specific architecture that is used.
        launcher: Launcher
            A custom launcher to use. If None, the arch launcher is used.
        launcher_flags: list[str]
            Additional flags to be added to the launcher invocation.

        Returns
        -------
        BenchmarkSummary:
            List of BenchmarkSummary objects that hold the output and the walltime
            of the benchmarks.
        """

        benchmarks = []
        for setup in self.setups:
            benchmarks.append(Benchmark(setup=setup))

        tasks = self._run_async(run_dir, job, arch, launcher, launcher_flags, benchmarks)

        return asyncio.run(tasks)
