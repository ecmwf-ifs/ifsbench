# Architecture classes

An {class}`~ifsbench.arch.Arch` object encapsulates everything that is specific
to a particular compute system:

* which {class}`~ifsbench.launch.Launcher` to use by default,
* any additional launcher flags that belong to this system,
* the hardware layout of each node ({class}`~ifsbench.job.CpuConfiguration`),
* system-specific environment variables.

Separating architecture concerns from the scientific setup means you can write a
benchmark once and run it on different machines simply by swapping the `Arch`
object.

---

## How `Arch.process_job` works

The central method is `process_job(job)`.
It receives a {class}`~ifsbench.job.Job` object describing what the benchmark
*wants* (number of tasks, CPUs per task, …) and returns an
{class}`~ifsbench.arch.ArchResult` that contains:

| Field | Meaning |
|---|---|
| `job` | An updated `Job` object with any architecture-calculated fields filled in. |
| `env_handlers` | Extra {class}`~ifsbench.env.EnvHandler` objects needed on this system. |
| `default_launcher` | The launcher to use if none was specified at run time. |
| `default_launcher_flags` | Additional flags passed to that launcher. |

The {class}`~ifsbench.benchmark.Benchmark` class calls `process_job` internally
before launching — you do not normally need to call it yourself.

---

## The built-in `DefaultArch`

{class}`~ifsbench.arch.DefaultArch` is a ready-to-use implementation with four
configurable attributes:

| Attribute | Type | Purpose |
|---|---|---|
| `launcher` | `Launcher` | The default launcher for this system. |
| `cpu_config` | `CpuConfiguration` | Hardware description of the nodes. |
| `set_explicit` | `bool` | If `True`, calculates and sets `tasks`, `nodes`, and `tasks_per_node` from `cpu_config`. |
| `launcher_flags` | `list[str]` | Extra flags always added to the launcher. |
| `env_handlers` | `list[EnvHandler]` | System-specific environment modifications. |

### Python example — SLURM cluster

```python
from ifsbench.arch import DefaultArch
from ifsbench.job import CpuConfiguration
from ifsbench.launch import SrunLauncher
from ifsbench.env import EnvHandler, EnvOperation

arch = DefaultArch(
    launcher=SrunLauncher(),
    cpu_config=CpuConfiguration(
        sockets_per_node=2,
        cores_per_socket=64,
        threads_per_core=1,
    ),
    set_explicit=True,
    launcher_flags=['--account=myproject', '--partition=compute'],
    env_handlers=[
        EnvHandler(mode=EnvOperation.SET, key='MPICH_ASYNC_PROGRESS', value='1'),
    ],
)
```

### YAML example

```yaml
arch:
  class_name: DefaultArch
  launcher:
    class_name: SrunLauncher
  cpu_config:
    sockets_per_node: 2
    cores_per_socket: 64
    threads_per_core: 1
  set_explicit: true
  launcher_flags:
    - --account=myproject
    - --partition=compute
  env_handlers:
    - mode: set
      key: MPICH_ASYNC_PROGRESS
      value: "1"
```

---

## Creating a custom `Arch`

If `DefaultArch` does not cover your needs, subclass {class}`~ifsbench.arch.Arch`
and implement the four abstract methods.

```python
from typing import List
from ifsbench.arch import Arch, ArchResult
from ifsbench.job import Job, CpuConfiguration
from ifsbench.launch import Launcher, SrunLauncher
from ifsbench.env import EnvHandler, EnvOperation

class MyHPCArch(Arch):
    """Architecture description for My HPC system."""

    # Pydantic fields that can be configured
    account: str
    partition: str = 'batch'

    def get_default_launcher(self) -> Launcher:
        return SrunLauncher()

    def get_default_launcher_flags(self) -> List[str]:
        return [f'--account={self.account}', f'--partition={self.partition}']

    def get_cpu_configuration(self) -> CpuConfiguration:
        return CpuConfiguration(
            sockets_per_node=2,
            cores_per_socket=64,
            threads_per_core=2,
            gpus_per_node=4,
        )

    def process_job(self, job: Job, **kwargs) -> ArchResult:
        result = ArchResult()
        result.job = job.clone()
        result.job.calculate_missing(self.get_cpu_configuration())
        result.default_launcher = self.get_default_launcher()
        result.default_launcher_flags = self.get_default_launcher_flags()
        # Add a system-wide environment variable
        result.env_handlers = [
            EnvHandler(mode=EnvOperation.SET, key='CRAY_CUDA_MPS', value='1'),
        ]
        return result
```

Because `MyHPCArch` inherits from
{class}`~ifsbench.serialisation_mixin.SubclassableSerialisationMixin` (via
{class}`~ifsbench.arch.Arch`), you can serialise and deserialise it:

```python
config = arch.dump_config(with_class=True)
# {'class_name': 'MyHPCArch', 'account': 'myproject', 'partition': 'batch'}

restored = Arch.from_config(config)
```

---

## Using an `Arch` when running a benchmark

Pass the `arch` object to {meth}`~ifsbench.benchmark.Benchmark.run`:

```python
from pathlib import Path
from ifsbench.benchmark import Benchmark

benchmark = Benchmark.from_config(...)  # loaded from YAML
arch = DefaultArch.from_config(...)

result = benchmark.run(run_dir=Path('/scratch/run'), arch=arch)
```

The `arch` object provides the launcher and updates the job;
you can still override both at call time if needed.
