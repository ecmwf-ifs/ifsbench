# Working with YAML files

ifsbench uses YAML files extensively to configure benchmarks. This tutorial explains
the mapping between Python objects and YAML, how to load YAML files, and the two
custom YAML constructors that ifsbench adds: `!include` and `!configure`.

---

## Python objects and YAML — the pydantic bridge

Most configuration classes in ifsbench inherit from either
{class}`~ifsbench.serialisation_mixin.SerialisationMixin` or
{class}`~ifsbench.serialisation_mixin.SubclassableSerialisationMixin`.
Both are thin wrappers around [pydantic](https://docs.pydantic.dev/) `BaseModel`
and provide two helper methods:

| Method | Purpose |
|---|---|
| `from_config(config)` | Create an instance from a plain Python dictionary. |
| `dump_config(with_class=False)` | Serialise the instance back to a plain dictionary. |

The plain dictionary is the bridge between Python objects and YAML.
A YAML file is loaded into a dictionary and then validated by pydantic,
which handles type coercion, validation, and default values automatically.

### Example

```python
from ifsbench.job import Job

# Create a Job object from a dictionary (as if loaded from YAML)
job = Job.from_config({'tasks': 128, 'nodes': 4, 'cpus_per_task': 8})

# Serialise it back to a dictionary
config = job.dump_config()
# {'tasks': 128, 'nodes': 4, 'cpus_per_task': 8}
```

### Polymorphic classes and `class_name`

Classes that inherit from
{class}`~ifsbench.serialisation_mixin.SubclassableSerialisationMixin` (such as
{class}`~ifsbench.launch.Launcher`, {class}`~ifsbench.data.DataHandler`, and
{class}`~ifsbench.arch.Arch`) can hold objects of different concrete subclasses.
pydantic needs to know which concrete class to instantiate, so a reserved key
`class_name` is automatically added to every serialised dictionary.

```python
from ifsbench.launch import SrunLauncher

launcher = SrunLauncher(flags=['--time=01:00:00'])
config = launcher.dump_config(with_class=True)
# {'class_name': 'SrunLauncher', 'flags': ['--time=01:00:00']}

# Reconstruct from config (base class does the dispatch):
from ifsbench.launch import Launcher
restored = Launcher.from_config(config)
```

In YAML this looks like:

```yaml
launcher:
  class_name: SrunLauncher
  flags:
    - --time=01:00:00
```

---

## Loading YAML files with `read_yaml`

{func}`~ifsbench.yaml.read_yaml` is the recommended entry point for loading any
ifsbench YAML file.

```python
from ifsbench.yaml import read_yaml

data = read_yaml('my_benchmark.yaml')
```

The function returns a plain Python dictionary.
You can pass the result (or a sub-section of it) directly to `from_config`:

```python
from ifsbench.benchmark import Benchmark

data = read_yaml('my_benchmark.yaml')
benchmark = Benchmark.from_config(data)
```

`read_yaml` supports an optional `encoding` parameter (default `'utf-8'`) in case
your files use a different character encoding.

---

## The `!include` constructor

Large configurations are easier to maintain when split across multiple files.
The `!include` constructor loads the content of another YAML file in-place.

```yaml
# benchmark.yaml
science_setup: !include science.yaml
job:
  tasks: 256
  nodes: 8
```

```yaml
# science.yaml
application:
  class_name: DefaultApplication
  command: [/path/to/my_executable]
```

The path given to `!include` must be **relative** to the file that contains the
directive (not to the working directory).
Absolute paths and paths that escape the directory tree with `../` are rejected.

Includes can be nested: a file loaded via `!include` may itself contain `!include`
directives.

---

## The `!configure` constructor

`!configure` is a lightweight templating mechanism.
It copies a block that already exists elsewhere in the same YAML document and
replaces `${placeholder}` strings with caller-supplied values.

### Syntax

```
key: !configure:<slash/separated/path/to/template>
  placeholder_one: value_one
  placeholder_two: value_two
```

The path after the colon (`:`), e.g. `templates/my_block`, is a slash-separated
navigation path into the YAML document, starting from its root.

### Example

```yaml
# Define reusable templates
templates:
  srun_job:
    launcher:
      class_name: SrunLauncher
      flags:
        - --account=${account}
        - --partition=${partition}
    job:
      tasks: ${tasks}
      cpus_per_task: ${cpus_per_task}

# Instantiate the template with concrete values
production_run: !configure:templates/srun_job
  account: myproject
  partition: compute
  tasks: 512
  cpus_per_task: 4

debug_run: !configure:templates/srun_job
  account: myproject
  partition: debug
  tasks: 16
  cpus_per_task: 1
```

After loading with `read_yaml`, `production_run` and `debug_run` are independent
copies of the template with all placeholders substituted.
The original `templates` block is left untouched.

### Combining `!include` and `!configure`

Templates can be defined in a separate file and included before use:

```yaml
# benchmark.yaml
templates: !include templates.yaml

benchmark_512: !configure:templates/hpc_run
  tasks: 512
  account: hpc-project
```

```yaml
# templates.yaml
hpc_run:
  job:
    tasks: ${tasks}
    nodes: 16
  launcher:
    class_name: SrunLauncher
    flags:
      - --account=${account}
```
