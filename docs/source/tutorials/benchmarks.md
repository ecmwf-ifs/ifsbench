# Benchmarks — ScienceSetup, TechSetup, and Benchmark

A {class}`~ifsbench.benchmark.Benchmark` in ifsbench is composed of three nested
objects:

* {class}`~ifsbench.benchmark.ScienceSetup` — *what* gets benchmarked and *how*.
* {class}`~ifsbench.benchmark.TechSetup` — optional technical overrides that do
  not change results (debug flags, alternative executables, extra environment
  variables).
* {class}`~ifsbench.job.Job` — the parallel resource request (tasks, nodes, …).

Together they form a {class}`~ifsbench.benchmark.BenchmarkSetup`, which is the
single mandatory field of {class}`~ifsbench.benchmark.Benchmark`.

---

## `ScienceSetup`

`ScienceSetup` describes everything that affects the *scientific outcome* of a
run:

| Field | Type | Purpose |
|---|---|---|
| `application` | `Application` | The executable to run (required). |
| `data_handlers_init` | `list[DataHandler]` | File operations run **once** when the run directory is first created. |
| `data_handlers_runtime` | `list[DataHandler]` | File operations run **every time** the benchmark is launched. |
| `env_handlers` | `list[EnvHandler]` | Environment variable changes applied at launch time. |

See {doc}`data_pipelines` for details on data and environment handlers.

```python
from ifsbench.benchmark import ScienceSetup
from ifsbench.application import DefaultApplication
from ifsbench.data import FetchHandler
from ifsbench.env import EnvHandler, EnvOperation
from pathlib import Path

science = ScienceSetup(
    application=DefaultApplication(command=['/opt/myapp/bin/myapp', '--nml', 'config.nml']),
    data_handlers_init=[
        FetchHandler(
            source_url='https://example.com/input.tar.gz',
            target_path=Path('input.tar.gz'),
        ),
    ],
    env_handlers=[
        EnvHandler(mode=EnvOperation.SET, key='OMP_NUM_THREADS', value='8'),
    ],
)
```

---

## `TechSetup`

`TechSetup` is optional and mirrors `ScienceSetup` but with different semantics:
it holds *technical* details that should not affect results.
Typical uses:

* Swap the production binary for a debug build.
* Add profiling or tracing environment variables.
* Inject additional data files needed only in certain testing scenarios.

| Field | Type | Purpose |
|---|---|---|
| `application` | `Application` or `None` | If set, overrides the application from `ScienceSetup`. |
| `data_handlers_init` | `list[DataHandler]` | Extra init-time file operations (appended to those in `ScienceSetup`). |
| `data_handlers_runtime` | `list[DataHandler]` | Extra runtime file operations (appended to those in `ScienceSetup`). |
| `env_handlers` | `list[EnvHandler]` | Extra environment variables (appended to those in `ScienceSetup`). |

```python
from ifsbench.benchmark import TechSetup
from ifsbench.env import EnvHandler, EnvOperation

tech = TechSetup(
    env_handlers=[
        EnvHandler(mode=EnvOperation.SET, key='DARSHAN_ENABLE', value='1'),
    ],
)
```

---

## Combining them into a `Benchmark`

```python
from ifsbench.benchmark import Benchmark, BenchmarkSetup
from ifsbench.job import Job

job = Job(tasks=256, nodes=8, cpus_per_task=4)

setup = BenchmarkSetup(science=science, job=job, tech=tech)
benchmark = Benchmark(setup=setup)
```

### Running the benchmark

```python
from pathlib import Path
from ifsbench.arch import DefaultArch

arch = DefaultArch.from_config({
    'launcher': {'class_name': 'SrunLauncher'},
    'cpu_config': {
        'sockets_per_node': 2,
        'cores_per_socket': 64,
        'threads_per_core': 1,
    },
    'set_explicit': True,
})

result = benchmark.run(run_dir=Path('/scratch/run'), arch=arch)
print(f'Walltime: {result.walltime:.2f} s')
```

The `run` method:

1. Calls `setup_rundir` to create the run directory and execute
   `data_handlers_init` (skipped if the directory already contains files and
   `force=False`).
2. Executes all `data_handlers_runtime`.
3. Builds an environment from the combined `env_handlers`.
4. Asks the `arch` (or the explicitly supplied launcher) to prepare the launch
   command.
5. Launches the executable and returns a
   {class}`~ifsbench.benchmark.BenchmarkSummary` with `stdout`, `stderr`, and
   `walltime`.

An asynchronous variant is also available:

```python
import asyncio

result = asyncio.run(benchmark.run_async(run_dir=Path('/scratch/run'), arch=arch))
```

---

## Full YAML example

A complete benchmark configuration in YAML:

```yaml
arch:
  class_name: DefaultArch
  cpu_config: {}
  launcher:
    class_name: MpirunLauncher

setup:
  job:
    tasks: 2

  science:
    application:
      class_name: DefaultApplication
      command:
        - ls
        - -l

    data_handlers_init:
      - class_name: FetchHandler
        source_url: https://github.com/ecmwf-ifs/ifsbench/archive/refs/tags/0.2.3.tar.gz
        target_path: ifsbench.tar.gz

      - class_name: ExtractHandler
        archive_path: ifsbench.tar.gz

    env_handlers:
      - mode: set
        key: OMP_NUM_THREADS
        value: "4"

  tech:
    env_handlers:
      - mode: set
        key: DARSHAN_ENABLE
        value: "1"
```

Loading and running from Python:

```python
from pathlib import Path
from ifsbench.yaml import read_yaml
from ifsbench.benchmark import Benchmark, BenchmarkSetup
from ifsbench.arch import Arch

data = read_yaml('benchmark.yaml')
benchmark_setup = BenchmarkSetup.from_config(data['setup'])
arch = Arch.from_config(data['arch'])

benchmark = Benchmark(setup=benchmark_setup)

result = benchmark.run(run_dir=Path('.'), arch=arch)
```

