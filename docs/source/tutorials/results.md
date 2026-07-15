# Result handling

ifsbench provides a small set of serialisable classes for storing and
summarising the numerical output of benchmark runs.
All of them live in the {mod}`ifsbench.results` package and are based on
{class}`~ifsbench.serialisation_mixin.SerialisationMixin`, so they can be saved
to and loaded from YAML/JSON files.

---

## `ResultData` and `ResultInfo`

{class}`~ifsbench.results.ResultData` is the base class for all result objects.
It holds a dictionary of named {class}`pandas.DataFrame` objects called
`frames`.

{class}`~ifsbench.results.ResultInfo` extends `ResultData` with optional
metadata about the run:

| Field | Type | Description |
|---|---|---|
| `frames` | `Dict[str, DataFrame]` | Named numerical result tables (required). |
| `stdout` | `str` or `None` | Standard output captured during the run. |
| `stderr` | `str` or `None` | Standard error captured during the run. |
| `walltime` | `float` or `None` | Wall-clock time of the run in seconds. |

### Creating result objects

```python
import pandas as pd
from ifsbench.results import ResultData, ResultInfo

# A simple result with one frame
result = ResultData(
    frames={
        'scores': pd.DataFrame(
            [[293.1, 1010.5], [294.3, 1008.2]],
            index=['Step 0', 'Step 1'],
            columns=['2m temperature', 'pressure'],
        )
    }
)

# A result with run metadata
result_info = ResultInfo(
    frames={
        'scores': pd.DataFrame(
            [[293.1, 1010.5], [294.3, 1008.2]],
            index=['Step 0', 'Step 1'],
            columns=['2m temperature', 'pressure'],
        )
    },
    stdout='Run completed successfully\n',
    walltime=142.7,
)
```

### Saving and loading results

All result objects support `dump_config` / `from_config` for serialisation:

```python
import json
from pathlib import Path
from ifsbench.results import ResultData

# Save to a JSON file
result_path = Path('result.json')
with result_path.open('w', encoding='utf-8') as f:
    json.dump(result.dump_config(), f, indent=2)

# Load back from the file
import yaml
with result_path.open('r', encoding='utf-8') as f:
    loaded = ResultData.from_config(json.load(f))

print(loaded.frames['scores'])
```

### Subclassing `ResultData`

You can subclass `ResultData` to add application-specific fields to your result
objects while keeping the serialisation support:

```python
from typing import Optional
from ifsbench.results import ResultData

class MyAppResult(ResultData):
    experiment_name: Optional[str] = None
    git_revision: Optional[str] = None

result = MyAppResult(
    frames={'output': my_frame},
    experiment_name='baseline_run',
    git_revision='abc1234',
)
```

---

## `EnsembleStats`

{class}`~ifsbench.results.EnsembleStats` aggregates results across multiple
ensemble members (or repeated runs) into a single set of statistical summaries.

It accepts a list of {class}`pandas.DataFrame` objects that must all share the
same index and column structure.

### Calculating statistics

Use {meth}`~ifsbench.results.EnsembleStats.calc_stats` to compute one or more
statistics at once.
The method returns a dictionary whose keys are the requested statistic names and
whose values are {class}`pandas.DataFrame` objects with the same shape as each
input frame.

Supported statistics:

| Keyword | Description |
|---|---|
| `'min'` | Element-wise minimum across members. |
| `'max'` | Element-wise maximum across members. |
| `'mean'` | Element-wise arithmetic mean. |
| `'median'` | Element-wise median. |
| `'sum'` | Element-wise sum. |
| `'std'` | Element-wise population standard deviation. |
| `'p10'`, `'P85'`, … | Any percentile between 0 and 100, case-insensitive. |

```python
import pandas as pd
from ifsbench.results import EnsembleStats

INDEX = ['Step 0', 'Step 1']
COLUMNS = ['2m temperature', 'pressure']

frames = [
    pd.DataFrame([[293, 1010], [294, 1008]], index=INDEX, columns=COLUMNS),
    pd.DataFrame([[296, 1012], [291, 1009]], index=INDEX, columns=COLUMNS),
    pd.DataFrame([[296, 1014], [292, 1005]], index=INDEX, columns=COLUMNS),
    pd.DataFrame([[295, 1008], [294, 1008]], index=INDEX, columns=COLUMNS),
]

stats = EnsembleStats(frames=frames)

# Single statistic
result = stats.calc_stats('mean')
print(result['mean'])

# Multiple statistics in one call
results = stats.calc_stats(['min', 'mean', 'max', 'p10', 'p90', 'std'])
for name, df in results.items():
    print(f'--- {name} ---')
    print(df)
```

### Serialising `EnsembleStats`

```python
import yaml
from pathlib import Path
from ifsbench.results import EnsembleStats

# Save
path = Path('ensemble_stats.yaml')
with path.open('w', encoding='utf-8') as f:
    yaml.dump(stats.dump_config(), f)

# Load
with path.open('r', encoding='utf-8') as f:
    loaded = EnsembleStats.from_config(yaml.safe_load(f))
```
