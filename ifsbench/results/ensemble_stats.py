# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import pathlib
import re
from typing import Dict, List, Union

import pandas as pd

__all__ = ['EnsembleStats', 'ENSEMBLE_DATA_PATH']

ENSEMBLE_DATA_PATH = 'ensemble_data'
AVAILABLE_BASIC_STATS = ['min', 'max', 'mean', 'median', 'sum', 'std']

_JSON_ORIENT = 'columns'


def _percentile(nth):
    def _qtile(data):
        return data.quantile(nth / 100.0)

    _qtile.__name__ = f'p{nth:02.0f}'
    return _qtile


class EnsembleStats:
    """Reads, writes, summarises results across ensemble members."""

    def __init__(self, data: List[pd.DataFrame]):
        self._raw_data = data
        dfc = pd.concat(data)
        self._group = dfc.groupby(dfc.index)

    @classmethod
    def from_data(cls, raw_data: List[pd.DataFrame]) -> 'EnsembleStats':
        """Create class from pandas data."""
        return cls(raw_data)

    @classmethod
    def from_config(cls, config: Dict[str, str]) -> 'EnsembleStats':
        """Read data from the file specified in the config."""
        if not ENSEMBLE_DATA_PATH in config:
            raise ValueError(f'missing config entry {ENSEMBLE_DATA_PATH}')
        if len(config) > 1:
            raise ValueError(
                f'unexpected entries in config: {config}, expected only {ENSEMBLE_DATA_PATH}'
            )
        input_path = pathlib.Path(config[ENSEMBLE_DATA_PATH])
        with open(input_path, 'r', encoding='utf-8') as jin:
            jdata = json.load(jin)
        dfs = [pd.DataFrame.from_dict(json.loads(entry)) for entry in jdata]
        return cls(dfs)

    def dump_data_to_json(self, output_file: Union[pathlib.Path, str]):
        """Output original data frames to json."""
        js = [df.to_json(orient=_JSON_ORIENT) for df in self._raw_data]
        with open(output_file, 'w', encoding='utf-8') as outf:
            json.dump(js, outf)

    def calc_stats(self, stats: Union[str, List[str]]) -> pd.DataFrame:
        """Calculate statistics.

        Desired statistics can be specified as a single string, e.g. 'mean', 'min',
        or as a list of strings. Supported stats are given by AVAILABLE_BASIC_STATS;
        in addition, percentiles between 0 and 100 can be specified as 'P10', 'p85', etc/
        """

        def std(x):
            # pandas uses sample standard deviation, we want population std.
            # Using function rather than lambda for the correct column name.
            return x.std(ddof=0)

        if isinstance(stats, str):
            stats = [stats]
        to_request = []
        for stat in stats:
            percentile_check = re.match(r'[p,P](\d{1,2})$', stat)
            if percentile_check:
                ptile_value = int(percentile_check.group(1))
                to_request.append(_percentile(ptile_value))
            elif stat == 'std':
                to_request.append(std)
            elif stat in AVAILABLE_BASIC_STATS:
                to_request.append(stat)
            else:
                raise ValueError(
                    f'Unknown stat: {stat}. Supported: {AVAILABLE_BASIC_STATS} and percentiles (e.g. p85).'
                )
        return self._group.agg(to_request)
