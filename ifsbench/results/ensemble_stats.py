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

from ifsbench.config_mixin import ConfigMixin

__all__ = ['EnsembleStats', 'ENSEMBLE_DATA_PATH_KEY', 'ENSEMBLE_DATA_KEY']

# keys of the config entries holding the path to the data file
# and the data.
ENSEMBLE_DATA_PATH_KEY = 'ensemble_data_file'
ENSEMBLE_DATA_KEY = 'ensemble_data'
# Statistics keywords available when calling calc_stats. In addition
# percentiles are supported with format '[p,P](\d{1,2})'.
AVAILABLE_BASIC_STATS = ['min', 'max', 'mean', 'median', 'sum', 'std']

_JSON_ORIENT = 'columns'


class EnsembleStats(ConfigMixin):
    """Reads, writes, summarises results across ensemble members."""

    _data_file = None

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
        """Read data from the json file specified in the config or
        directly from the in-line data.

        Args:
            config: dictionary specifying either path to a file containing
                the data or containing the data in-line.
        """
        if len(config) > 1:
            raise ValueError(
                f'unexpected entries in config for EnsembleStats: {config}'
            )
        if ENSEMBLE_DATA_PATH_KEY in config:
            input_path = pathlib.Path(config[ENSEMBLE_DATA_PATH_KEY])
            with open(input_path, 'r', encoding='utf-8') as jin:
                data = json.load(jin)
            dfs = [pd.DataFrame.from_dict(json.loads(entry)) for entry in data]
            es = cls(dfs)
            es._data_file = config[ENSEMBLE_DATA_PATH_KEY]
            return es
        if ENSEMBLE_DATA_KEY in config:
            data = config[ENSEMBLE_DATA_KEY]
            dfs = [pd.DataFrame.from_dict(entry) for entry in data]
            es = cls(dfs)
            return es

        raise ValueError(
            f'missing config entry: either {ENSEMBLE_DATA_PATH_KEY} or {ENSEMBLE_DATA_KEY}'
        )

    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, List]]:
        config = {}
        if not self._data_file:
            config[ENSEMBLE_DATA_KEY] = [df.to_dict() for df in self._raw_data]
        else:
            config[ENSEMBLE_DATA_PATH_KEY] = self._data_file
        if with_class:
            config['classname'] = type(self).__name__
        return config

    def dump_data_to_json(self, output_file: Union[pathlib.Path, str]):
        """Output original data frames to json."""
        self._data_file = str(output_file)
        js = [df.to_json(orient=_JSON_ORIENT) for df in self._raw_data]
        with open(output_file, 'w', encoding='utf-8') as outf:
            json.dump(js, outf)

    def calc_stats(self, stats: Union[str, List[str]]) -> Dict[str, pd.DataFrame]:
        """Calculate statistics.

        Desired statistics can be specified as a single string, e.g. 'mean', 'min',
        or as a list of strings. Supported stats are given by AVAILABLE_BASIC_STATS;
        in addition, percentiles between 0 and 100 can be specified as 'P10', 'p85', etc.

        Args:
            stats: string representation or list or string representations of stats values
                to be calculated.
        Returns:
            Dictionary or results with requested stat string representations as key and
                dataframes of results for that stat as value.
        """

        def std(x):
            # pandas uses sample standard deviation, we want population std.
            # Using function rather than lambda for the correct column name.
            return x.std(ddof=0)

        def _percentile(stat_name: str, nth: float):
            def _qtile(data):
                return data.quantile(nth / 100.0)

            _qtile.__name__ = stat_name
            return _qtile

        if isinstance(stats, str):
            stats = [stats]
        to_request = []
        for stat in stats:
            percentile_check = re.match(r'[p,P](\d{1,3})$', stat)
            if percentile_check:
                ptile_value = int(percentile_check.group(1))
                if ptile_value > 100:
                    raise ValueError(
                        f'Percentile has to be in [0, 100], got {ptile_value}.'
                    )
                to_request.append(_percentile(stat, ptile_value))
            elif stat == 'std':
                to_request.append(std)
            elif stat in AVAILABLE_BASIC_STATS:
                to_request.append(stat)
            else:
                raise ValueError(
                    f'Unknown stat: {stat}. Supported: {AVAILABLE_BASIC_STATS} and percentiles (e.g. p85).'
                )
        df = self._group.agg(to_request)
        return {stat: df.xs(stat, level=1, axis=1) for stat in stats}
