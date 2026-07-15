# Launchers

A {class}`~ifsbench.launch.Launcher` is responsible for building the command
line that will actually run a parallel executable.
Given a {class}`~ifsbench.job.Job` specification (number of tasks, nodes, CPU
binding, …) it produces a {class}`~ifsbench.launch.LaunchData` object containing
the final command and environment, which can then be executed.

---

## The Launcher hierarchy

```
Launcher  (abstract)
├── DirectLauncher   – runs the command directly, optionally via a wrapper binary
├── SrunLauncher     – builds a srun (SLURM) invocation
└── MpirunLauncher   – builds an mpirun invocation

LauncherWrapper  (abstract)
├── DDTLauncher      – wraps any launch command with Linaro DDT
└── BashLauncher     – writes the command to a bash script instead of running it directly

CompositeLauncher    – combines a base Launcher with one or more LauncherWrappers
```

---

## Basic launchers

### `DirectLauncher`

Runs the application directly.
An optional `executable` attribute lets you prepend a wrapper binary (e.g. a
profiler or a container runtime).

```python
from ifsbench.launch import DirectLauncher

# Execute the command as-is
launcher = DirectLauncher()

# Wrap it with an arbitrary binary
launcher = DirectLauncher(executable='time', flags=['-v'])
```

### `SrunLauncher`

Translates {class}`~ifsbench.job.Job` attributes into `srun` flags.

```python
from ifsbench.launch import SrunLauncher
from ifsbench.job import Job, CpuBinding

launcher = SrunLauncher(flags=['--time=02:00:00'])
job = Job(tasks=256, nodes=8, cpus_per_task=4, bind=CpuBinding.BIND_CORES)
```

When `cpus_per_task` is set, `OMP_NUM_THREADS` is automatically added to the
environment.

### `MpirunLauncher`

Similar to `SrunLauncher` but targets a standard `mpirun` binary.

```python
from ifsbench.launch import MpirunLauncher

launcher = MpirunLauncher(flags=['--oversubscribe'])
```

---

## Launcher wrappers

A {class}`~ifsbench.launch.launcher.LauncherWrapper` is not a standalone launcher —
it *wraps* the {class}`~ifsbench.launch.LaunchData` produced by a base launcher and
modifies it.

### `DDTLauncher`

Prepends `ddt --` to the existing command so that the application is launched
inside a [Linaro DDT](https://www.linaroforge.com/linaroDdt/) debug session.

```python
from ifsbench.launch.ddtlauncher import DDTLauncher

ddt = DDTLauncher(flags=['--offline'])
```

### `BashLauncher`

Instead of running the command directly, it writes it to a dated bash script
(under `run_dir/bash_scripts/`) and executes that.
This is useful for auditing — you always have a record of exactly what was run.

```python
from ifsbench.launch.bashlauncher import BashLauncher

bash_wrapper = BashLauncher()
```

---

## Combining launchers with `CompositeLauncher`

{class}`~ifsbench.launch.CompositeLauncher` takes a base launcher and an ordered
list of wrappers.
The base launcher builds the initial {class}`~ifsbench.launch.LaunchData`;
each wrapper then transforms it in sequence.

### Python example

```python
from ifsbench.launch import CompositeLauncher, SrunLauncher
from ifsbench.launch.bashlauncher import BashLauncher

# srun → dump launch command to bash script and run
launcher = CompositeLauncher(
    base_launcher=SrunLauncher(flags=['--time=01:00:00']),
    wrappers=[
        BashLauncher(),
    ],
)
```

### YAML example

```yaml
launcher:
  class_name: CompositeLauncher
  base_launcher:
    class_name: SrunLauncher
    flags:
      - --time=01:00:00
  wrappers:
    - class_name: BashLauncher
```

---

## Command-line launcher options

`ifsbench` provides a set of [click](https://click.palletsprojects.com/) helpers
that make it easy to expose launcher configuration in your own run scripts.

### `launcher_options` decorator

{func}`~ifsbench.command_line.click_launcher.launcher_options` is a click
decorator that adds two options to any `@click.command`:

| Option | Short | Description |
|---|---|---|
| `--launcher-config` | — | Path to a YAML file containing a full launcher configuration. |
| `--launcher-flags` / `-f` | `-f` | Extra flags forwarded to the launcher (repeatable). |

The decorated function receives a
{class}`~ifsbench.command_line.click_launcher.LauncherBuilder` instance under
the keyword argument `launcher_builder`.

```python
import click
from ifsbench.command_line.click_launcher import launcher_options

@click.command()
@launcher_options
def run(launcher_builder):
    launcher = launcher_builder.build_launcher()
    # use launcher …
```

Invocation examples:

```bash
# Use the default launcher from the Arch object (no extra flags)
python run.py

# Load a complete launcher from a YAML file
python run.py --launcher-config srun_config.yaml

# Add extra srun flags without replacing the default launcher
python run.py -f '--time=02:00:00' -f '--account=myproject'
```

### `LauncherBuilder`

{class}`~ifsbench.command_line.click_launcher.LauncherBuilder` collects the
command-line arguments and turns them into a concrete
{class}`~ifsbench.launch.Launcher` object.

| Method | Description |
|---|---|
| `build_from_arch(arch)` | Build a launcher, falling back to the default launcher defined by an {class}`~ifsbench.arch.Arch` object when no `--launcher-config` is given. |
| `build_launcher(default_launcher, default_launcher_flags)` | Lower-level variant; supply defaults explicitly. |

**Priority rules:**

1. If `--launcher-config` is provided, the launcher is loaded from the YAML file
   and any `--launcher-flags` are appended to it.
2. Otherwise the `default_launcher` (typically from the `Arch`) is used and
   `--launcher-flags` are appended to it.
3. If neither is available, `None` is returned (meaning no launcher wrapping).

```python
from pathlib import Path
from ifsbench.arch import DefaultArch
from ifsbench.command_line.click_launcher import LauncherBuilder

arch = DefaultArch.from_config({
    'launcher': {'class_name': 'SrunLauncher'},
    'cpu_config': {
        'sockets_per_node': 2,
        'cores_per_socket': 64,
        'threads_per_core': 1,
    },
})

builder = LauncherBuilder()
builder.launcher_flags = ['--time=01:00:00', '--account=myproject']

launcher = builder.build_from_arch(arch)
```

### YAML launcher configuration file

The `--launcher-config` option accepts any YAML file that can be loaded via
{meth}`~ifsbench.launch.Launcher.from_config`.
For example:

```yaml
# srun_config.yaml
class_name: SrunLauncher
flags:
  - --time=02:00:00
  - --partition=gpu
```

```bash
python run.py --launcher-config srun_config.yaml -f '--account=myproject'
```

---

## Standalone usage

A launcher can be used independently of a full benchmark setup.
Call `prepare` to obtain a {class}`~ifsbench.launch.LaunchData` object, then
call `launch` (or `launch_async`) on it.

```python
from pathlib import Path
from ifsbench.launch import SrunLauncher
from ifsbench.job import Job
from ifsbench.env import DefaultEnvPipeline, EnvHandler, EnvOperation
import os

launcher = SrunLauncher()
job = Job(tasks=32, nodes=1, cpus_per_task=4)

env_pipeline = DefaultEnvPipeline(env_initial=os.environ)
env_pipeline.add(EnvHandler(mode=EnvOperation.SET, key='MY_VAR', value='hello'))

launch_data = launcher.prepare(
    run_dir=Path('/scratch/run'),
    job=job,
    cmd=['/opt/myapp/bin/myapp', '--config', 'config.nml'],
    env_pipeline=env_pipeline,
)

result = launch_data.launch()
print('Exit code:', result.exit_code)
print('Wall time:', result.wall_time, 'seconds')
```
