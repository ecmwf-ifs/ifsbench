# Result validation

After a benchmark run you often need to verify that the numerical output has not
changed compared to a known-good reference.
ifsbench provides two tools for this:

* {class}`~ifsbench.validation.FrameCloseValidation` — compares two
  {class}`pandas.DataFrame` objects element-wise using `numpy.isclose`.
* {func}`~ifsbench.validation.validate_result_identical` — high-level helper
  that loads a {class}`~ifsbench.results.ResultData` object from a file (or
  accepts one in memory) and compares it against a stored reference file.

---

## `FrameCloseValidation`

{class}`~ifsbench.validation.FrameCloseValidation` performs a
column-by-column comparison of two DataFrames, ignoring non-float columns.
It wraps `numpy.isclose` so you can specify both absolute and relative
tolerances.

| Parameter | Default | Description |
|---|---|---|
| `atol` | `0` | Absolute tolerance. |
| `rtol` | `0` | Relative tolerance. |

### `compare` method

```python
equal, mismatch = validator.compare(frame1, frame2)
```

**Returns:**

* `equal` (`bool`) — `True` when all float values are within the specified
  tolerances (and non-float columns are identical in shape and type).
* `mismatch` (`list` of `(index, column)` tuples) — the positions of the first
  set of differing values, or an empty list when the frames differ in shape or
  dtype.

### Examples

```python
import pandas as pd
from ifsbench.validation import FrameCloseValidation

frame1 = pd.DataFrame(
    [[293.0, 1010.5], [294.3, 1008.2]],
    index=['Step 0', 'Step 1'],
    columns=['2m temperature', 'pressure'],
)
frame2 = pd.DataFrame(
    [[293.0001, 1010.5], [294.3, 1008.2001]],
    index=['Step 0', 'Step 1'],
    columns=['2m temperature', 'pressure'],
)

# Exact comparison (default tolerances)
validator = FrameCloseValidation()
equal, mismatch = validator.compare(frame1, frame2)
print(equal)    # False
print(mismatch) # [('Step 0', '2m temperature'), ('Step 1', 'pressure')]

# Relaxed comparison
validator = FrameCloseValidation(atol=1e-3)
equal, mismatch = validator.compare(frame1, frame2)
print(equal)    # True
print(mismatch) # []
```

Non-float columns are stripped before comparison, so integer or string columns
do not affect the result:

```python
frame_with_int_col = pd.DataFrame(
    [[293.0, 1010.5, 42], [294.3, 1008.2, 43]],
    columns=['temperature', 'pressure', 'step'],
)
# The 'step' column (int) is ignored; only 'temperature' and 'pressure' are compared.
```

---

## `validate_result_identical`

{func}`~ifsbench.validation.validate_result_identical` is a convenience wrapper
around {class}`~ifsbench.validation.FrameCloseValidation` that works directly
with {class}`~ifsbench.results.ResultData` objects.

```python
from pathlib import Path
from ifsbench.validation import validate_result_identical
from ifsbench.results import ResultData

is_ok = validate_result_identical(
    result=result_or_path,
    reference_path=Path('reference.yaml'),
    result_type=ResultData,
    atol=1e-6,
    rtol=1e-6,
)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `result` | `str`, `Path`, or `ResultData` | The result to validate. Pass a file path or an in-memory object. |
| `reference_path` | `Path` | Path to a YAML/JSON file holding the reference `ResultData`. |
| `result_type` | `Type[ResultData]` | The concrete `ResultData` subclass to use when loading from file. |
| `atol` | `float` | Absolute tolerance (default: `0`). |
| `rtol` | `float` | Relative tolerance (default: `0`). |

**Returns** `True` when every frame in `result` is within tolerance of the
corresponding reference frame, `False` otherwise.
Diagnostic messages are emitted via the ifsbench logger (see `--debug` / `--log`
in the CLI).

### Creating a reference file

```python
import json
from pathlib import Path
import pandas as pd
from ifsbench.results import ResultData

reference = ResultData(
    frames={
        'scores': pd.DataFrame(
            [[293.0, 1010.5], [294.3, 1008.2]],
            index=['Step 0', 'Step 1'],
            columns=['2m temperature', 'pressure'],
        )
    }
)

reference_path = Path('reference.json')
with reference_path.open('w', encoding='utf-8') as f:
    json.dump(reference.dump_config(), f, indent=2)
```

### Validating an in-memory result

```python
from ifsbench.results import ResultData
from ifsbench.validation import validate_result_identical

new_result = ResultData(frames={'scores': my_output_frame})

ok = validate_result_identical(
    result=new_result,
    reference_path=reference_path,
    result_type=ResultData,
    atol=1e-5,
)

if not ok:
    raise RuntimeError('Results differ from reference!')
```

### Validating a result from file

If the result is already saved on disk:

```python
from pathlib import Path
from ifsbench.results import ResultData
from ifsbench.validation import validate_result_identical

ok = validate_result_identical(
    result=Path('result.json'),
    reference_path=Path('reference.json'),
    result_type=ResultData,
)
```

### Using a custom `ResultData` subclass

When your application uses a subclass of `ResultData`, pass that subclass as
`result_type` so that extra fields are deserialised correctly:

```python
from ifsbench.results import ResultData
from ifsbench.validation import validate_result_identical

class MyAppResult(ResultData):
    experiment_name: str = ''

ok = validate_result_identical(
    result=Path('my_result.json'),
    reference_path=Path('my_reference.json'),
    result_type=MyAppResult,
)
```

---

## Combining validation with a benchmark run

A typical workflow is to run a benchmark, save the result, and then compare it
to a stored reference:

```python
import json
from pathlib import Path
from ifsbench.benchmark import Benchmark
from ifsbench.arch import DefaultArch
from ifsbench.results import ResultData
from ifsbench.validation import validate_result_identical

arch = DefaultArch.from_config(arch_config)
benchmark = Benchmark.from_config(benchmark_config)

summary = benchmark.run(run_dir=Path('/scratch/run'), arch=arch)

# Parse the application output into a ResultData object (application-specific)
result = parse_output(summary.stdout)

# Optionally persist the result
result_path = Path('/scratch/run/result.json')
with result_path.open('w', encoding='utf-8') as f:
    json.dump(result.dump_config(), f, indent=2)

# Validate
ok = validate_result_identical(
    result=result,
    reference_path=Path('reference/result.json'),
    result_type=ResultData,
    atol=1e-6,
    rtol=1e-6,
)
assert ok, 'Validation failed: results differ from reference'
```
