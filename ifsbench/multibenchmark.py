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
from dataclasses import dataclass
import itertools
from pathlib import Path
from typing import List, Optional


from ifsbench.arch import Arch
from ifsbench.benchmark import Benchmark, BenchmarkSetup, BenchmarkSummary, ScienceSetup, TechSetup
from ifsbench.job import Job
from ifsbench.launch import Launcher
from ifsbench.logging import debug
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

    @dataclass
    class BenchmarkAndPath:
        benchmark: Benchmark
        run_dir: Path

    def _sub_run_dir(self, run_dir: Path, run_number: int) -> Path:
        sub_dir = SUBDIRECTORY_PREFIX + str(run_number)
        return run_dir / sub_dir

    async def _run_async(
        self,
        benchmarks: List[BenchmarkAndPath],
        job: Optional[Job] = None,
        arch: Optional[Arch] = None,
        launcher: Optional[Launcher] = None,
        launcher_flags: Optional[List[str]] = None,
    ) -> List[BenchmarkSummary]:

        tasks = [
            asyncio.create_task(
                benchmark_and_path.benchmark.run_async(
                    benchmark_and_path.run_dir, job, arch, launcher, launcher_flags
                )
            )
            for benchmark_and_path in benchmarks
        ]
        return await asyncio.gather(*tasks)

    def run(
        self,
        run_dir: Path,
        job: Optional[Job] = None,
        arch: Optional[Arch] = None,
        launcher: Optional[Launcher] = None,
        launcher_flags: Optional[List[str]] = None,
        max_parallel: Optional[int] = None,
    ) -> List[BenchmarkSummary]:
        """
        Run the benchmarks.

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
        max_parallel: int
            Maximum number of benchmark to run in parallel.
            If None, all benchmark will be run together.
            Otherwise, the list will be split into chunks of the specified size.
            The benchmark in each chunk will run in parallel, and the chunks will run one after the other.

        Returns
        -------
        BenchmarkSummary:
            List of BenchmarkSummary objects that hold the output and the walltime
            of the benchmarks.
        """

        run_dir.mkdir(parents=True, exist_ok=True)

        if max_parallel is not None and max_parallel < 1:
            raise RuntimeError(
                f'Invalid value for maximum value of parallel runs, must be larger 0, was max_parallel={max_parallel}'
            )

        benchmarks = []
        for i, setup in enumerate(self.setups):
            benchmarks.append(
                self.BenchmarkAndPath(
                    benchmark=Benchmark(setup=setup), run_dir=self._sub_run_dir(run_dir, i)
                )
            )

        chunks = []

        if max_parallel:
            for i in range(0, len(benchmarks), max_parallel):
                chunks.append(benchmarks[i : i + max_parallel])
        else:
            chunks.append(benchmarks)

        debug(f'Running benchmarks in {len(chunks)} set(s) of size {len(chunks[0])}')

        results = []

        for chunk in chunks:
            tasks = self._run_async(chunk, job, arch, launcher, launcher_flags)
            chunk_result = asyncio.run(tasks)
            results.extend(chunk_result)

        return results

    @classmethod
    def from_setup_lists(
        cls,
        science_setups: List[ScienceSetup],
        jobs: List[Job],
        tech_setups: Optional[List[TechSetup]] = None,
    ) -> 'MultiBenchmark':
        """
        Create MultiBenchmark with setups from the cartesian product of the lists.

        Parameters
        ----------
        science_setups: list[ScienceSetup]
            The science setups used to create the BenchmarkSetup
        jobs: list[Job]
            The jobs used to create the BenchmarkSetup
        tech_setups: list[TechSetup]
            Optional tech setups used to create the BenchmarkSetup

        Returns
        -------
        MultiBenchmark:
            MultiBenchmark with list of setups based on all possible combinations of the input lists.
        """

        if tech_setups is None:
            tech_setups = [None]
        setup_combos = itertools.product(science_setups, jobs, tech_setups)

        setups = [
            BenchmarkSetup(science=science, job=job, tech=tech)
            for science, job, tech in setup_combos
        ]
        return cls(setups=setups)
