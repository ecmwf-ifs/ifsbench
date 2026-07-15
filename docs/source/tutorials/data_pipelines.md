# Data and environment pipelines

A *data pipeline* in ifsbench is a sequence of operations that prepare the run
directory before an executable is launched. Similarly, *environment pipelines*
can be used to set up environment variables before the launch.
These pipelines are based on the following abstract base classes:

* {class}`~ifsbench.data.DataHandler` — operates on files and directories.
* {class}`~ifsbench.env.EnvHandler` — modifies environment variables.

Both are pydantic-based serialisable objects, so they can be created in Python
or loaded from YAML (see {doc}`yaml_files`).

---

## File operations — `DataHandler`

{class}`~ifsbench.data.DataHandler` is the abstract base class for all file
pipeline steps.
Each concrete handler implements a single `execute(wdir)` method that performs
its operation relative to the given working directory.

### Available handlers

| Class | What it does |
|---|---|
| {class}`~ifsbench.data.FetchHandler` | Downloads a file from a URL. |
| {class}`~ifsbench.data.RenameHandler` | Copies, moves, or symlinks files using regex patterns. |
| {class}`~ifsbench.data.ExtractHandler` | Extracts an archive into a directory. |
| {class}`~ifsbench.data.NamelistHandler` | Writes or patches a Fortran namelist file. |
| {class}`~ifsbench.data.PerturbationHandler` | Applies perturbations to a data file. |

### Python example

```python
from pathlib import Path
from ifsbench.data import FetchHandler, ExtractHandler, RenameHandler
from ifsbench.data.renamehandler import RenameMode

run_dir = Path('/scratch/my_run')

# 1. Download an archive
fetch = FetchHandler(
    source_url='https://example.com/input_data.tar.gz',
    target_path=Path('input_data.tar.gz'),
)

# 2. Extract the archive
extract = ExtractHandler(
    archive_path=Path('input_data.tar.gz'),
)

# 3. Create a symlink so the executable can find the file under an expected name
rename = RenameHandler(
    pattern=r'input_data_v2\.nc',
    repl='input.nc',
    mode=RenameMode.SYMLINK,
)

# Execute the pipeline steps in order
for handler in [fetch, extract, rename]:
    handler.execute(run_dir)
```

### YAML example

```yaml
data_handlers_init:
  - class_name: FetchHandler
    source_url: https://example.com/input_data.tar.gz
    target_path: input_data.tar.gz

  - class_name: ExtractHandler
    archive_path: input_data.tar.gz

  - class_name: RenameHandler
    pattern: input_data_v2\.nc
    repl: input.nc
    mode: symlink
```

---

## Environment pipelines — `EnvHandler` and `EnvPipeline`

{class}`~ifsbench.env.EnvHandler` describes a single change to the process
environment.
The supported operations are defined by the {class}`~ifsbench.env.EnvOperation`
enum:

| Operation | Effect |
|---|---|
| `set` | Set a variable to a given value. |
| `append` | Append a value to an existing variable (using `:`). |
| `prepend` | Prepend a value to an existing variable (using `:`). |
| `delete` | Remove a variable from the environment. |
| `clear` | Remove **all** variables from the environment. |

{class}`~ifsbench.env.DefaultEnvPipeline` collects a list of
{class}`~ifsbench.env.EnvHandler` objects and executes them in order,
producing a final environment dictionary.

### Python example

```python
import os
from ifsbench.env import EnvHandler, EnvOperation, DefaultEnvPipeline

pipeline = DefaultEnvPipeline(env_initial=os.environ)

# Set OMP_NUM_THREADS
pipeline.add(EnvHandler(mode=EnvOperation.SET, key='OMP_NUM_THREADS', value='8'))

# Append a library path
pipeline.add(EnvHandler(
    mode=EnvOperation.APPEND,
    key='LD_LIBRARY_PATH',
    value='/opt/mylib/lib',
))

# Remove a variable that could interfere
pipeline.add(EnvHandler(mode=EnvOperation.DELETE, key='LD_PRELOAD'))

env = pipeline.execute()  # returns a plain dict
```

### YAML example

```yaml
env_handlers:
  - mode: set
    key: OMP_NUM_THREADS
    value: "8"

  - mode: append
    key: LD_LIBRARY_PATH
    value: /opt/mylib/lib

  - mode: delete
    key: LD_PRELOAD
```

---

## Using pipelines inside a benchmark

In practice you rarely build pipelines manually.
Instead, you attach {class}`~ifsbench.data.DataHandler` and
{class}`~ifsbench.env.EnvHandler` lists to a
{class}`~ifsbench.benchmark.ScienceSetup` or
{class}`~ifsbench.benchmark.TechSetup` and let the
{class}`~ifsbench.benchmark.Benchmark` class execute them at the right moment:

* `data_handlers_init` — run once when the run directory is first created.
* `data_handlers_runtime` — run every time the benchmark is launched.
* `env_handlers` — applied to the process environment at launch time.

See {doc}`benchmarks` for a complete worked example.
