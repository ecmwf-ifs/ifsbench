# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
from pathlib import Path
import re
from typing import List, Optional, Set

import pandas as pd
import xarray as xr

from ifsbench.config_mixin import DataClass
from ifsbench.netcdf_file_reader import NetcdfFileReader
from ifsbench.gribfile import GribFileReader


__all__ = [
    'DataFileType',
    'DataFileStats',
]

# Dimensions over which to calculate statistics. Other dimensions will be kept separate.
_DEFAULT_STAT_DIMS = set(['values', 'latitudes', 'longitudes'])

# Statistics to calculate, has to be implemented in _calc_stat.
# Percentiles have to be given in a form that matches r'[p,P](\d{1,2})$'.
_DEFAULT_STAT_NAMES = ['mean', 'min', 'max', 'p5', 'p10', 'p90', 'p95']

# Dimension name to add to statistics datasets and use for merging.
# This will be the column name in the dataframe with values from
# _STAT_NAMES
_STAT_DIM_NAME = 'stat'


class DataFileType(str, Enum):
    """Supported data file types.

    Used to specify file type if automatic check is not possible.
    """

    GRIB = 'grib'
    NETCDF = 'netcdf'


_reader_from_file_type = {
    DataFileType.GRIB: GribFileReader,
    DataFileType.NETCDF: NetcdfFileReader,
}


class DataFileStats(DataClass):
    """
    Calculate various statistics from the data in a file.

    Parameters
    ----------
    input_path: str
        The path to the input data file.
    filetype: DataFielType | None
        Data type of file.
        If None, will be determined from file header if possible.
    stat_dims: set[str]
        Dimensions over which to calculate the statistics.
    stat_names: list[str]
        List of statistics values to calculate, e.g. ['min', 'mean']
    """

    input_path: Path
    filetype: Optional[DataFileType] = None
    stat_dims: Set[str] = _DEFAULT_STAT_DIMS
    stat_names: List[str] = _DEFAULT_STAT_NAMES

    _stats = []

    def get_stats(
        self,
    ) -> List[pd.DataFrame]:
        """Create dataframe with statistics over location.

        Dimensions to calculate the statistics over are specified by
        _STAT_DIMS, other dimensions are preserved.
        Statistics to calculate are given by _STAT_NAMES.

        Returns:
            List of dataframes containing the requested statistics.
        """
        if self._stats:
            return self._stats

        reader_type = _reader_from_file_type[self.filetype] if self.filetype else None

        if not reader_type:
            with open(self.input_path, 'rb') as f:
                header = f.read(4)
            if b'GRIB' in header:
                reader_type = GribFileReader
            elif b'CDF' in header or b'HDF' in header:
                reader_type = NetcdfFileReader
            else:
                raise ValueError(
                    f'Unable to determine data file type for {self.input_path}'
                )

        dss = reader_type().read_data(self.input_path)
        for ds in dss:
            _stat_dims = list(set(ds.sizes.keys()) & self.stat_dims)
            stats_dss = [
                self._create_stat_ds(ds, stat_name, _stat_dims)
                for stat_name in self.stat_names
            ]
            ds_stats = xr.concat(stats_dss, dim=_STAT_DIM_NAME)
            self._stats.append(ds_stats.to_dataframe())
        return self._stats

    @classmethod
    def _calc_stat(
        cls, ds: xr.Dataset, stat_name: str, stat_dims: List[str]
    ) -> xr.Dataset:
        """Creates datasets containing the statistical value specified by stat_name."""
        if stat_name == 'mean':
            return ds.mean(dim=stat_dims)
        if stat_name == 'min':
            return ds.min(dim=stat_dims)
        if stat_name == 'max':
            return ds.max(dim=stat_dims)

        percentile_check = re.match(r'[p,P](\d{1,2})$', stat_name)
        if percentile_check:
            percentile = int(percentile_check.group(1))
            ds_stat = ds.quantile(percentile / 100.0, dim=stat_dims)
            # `quantile` removes dimensionless coordinates and adds a new coordinate 'quantiles'.
            # This has to be undone to match the other stats datasets.
            ds_stat = ds_stat.drop_vars('quantile').assign_coords(ds.coords)
            dims_to_drop = list(set(ds_stat.sizes.keys()) & set(stat_dims))
            return ds_stat.drop_dims(dims_to_drop)

        raise ValueError(f'Unknown stat requested: {stat_name}')

    @classmethod
    def _create_stat_ds(
        cls, ds: xr.Dataset, stat_name: str, stat_dims: List[str]
    ) -> xr.Dataset:
        ds_stat = cls._calc_stat(ds, stat_name, stat_dims)
        return ds_stat.assign_coords({_STAT_DIM_NAME: stat_name}).expand_dims(
            _STAT_DIM_NAME
        )
