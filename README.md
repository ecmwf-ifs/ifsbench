# IFSBench - A pythonic benchmarking package for IFS development

[![license](https://img.shields.io/github/license/ecmwf-ifs/ifsbench)](https://www.apache.org/licenses/LICENSE-2.0.html)
[![pytest](https://github.com/ecmwf-ifs/ifsbench/actions/workflows/pytest.yaml/badge.svg)](https://github.com/ecmwf-ifs/ifsbench/actions/workflows/pytest.yaml)
[![codecov](https://codecov.io/github/ecmwf-ifs/ifsbench/graph/badge.svg?token=K0617536LF)](https://codecov.io/github/ecmwf-ifs/ifsbench)

**NOTE**: _This is work-in-progress and represents a prototype, not a full solution!_

IFSBench is a prototype tool that aims to provide Python-based
testing and performance benchmarking capabilities for IFS development
workflows. It is based on Python wrapper classes and tools to create
a set of lightweight benchmark scripts that provide additional features
and a more "pythonic" flavour of tooling. The primary planned features are:

* Configurable per-test benchmark scripts with an improved CLI
  (command-line interface).
* Reference benchmark results are processed as pandas.DataFrame
  objects and can be stored (and thus version-controlled) in a variety
  of light-weight formats (eg, .csv) without the need for complete log
  files.
* Large benchmark setups (eg. tl159-fc or tco399-fc) that can symlink,
  copy or download necessary input data from pre-defined locations and
  thus do not need git(-lfs) or cmake-based symlinking at configure
  time.
* Ability to parse DrHook profiles (thanks to Iain Miller!) into
  commonly accessible formats (again based on pandas.DataFrames), as
  well as the traditional test-based output format.

## Contact

Michael Lange (michael.lange@ecmwf.int),
Balthasar Reuter (balthasar.reuter@ecmwf.int),
Johannes Bulin (johannes.bulin@ecmwf.int)

## Licence

License: [Apache License 2.0](LICENSE) In applying this licence, ECMWF does not waive the privileges and immunities
granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.

## Contributing

Contributions to `ifsbench` are welcome. In order to do so, please open an issue where
a feature request or bug can be discussed. Then create a pull request with your
contribution and sign the [contributors license agreement (CLA)](https://bol-claassistant.ecmwf.int/ecmwf-ifs/ifsbench).

## Installation

See [INSTALL.md](INSTALL.md).

## Coding style

The code should be checked with pylint in order to conform with the standards
specified in `.pylintrc`:
```
<build_dir>/ifsbench_env/bin/pylint --rcfile=.pylintrc ifsbench/ tests/
```
