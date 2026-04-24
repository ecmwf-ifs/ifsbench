# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import warnings
from typing import List

import xarray as xr

from ifsbench.data_file_reader import DataFileReader

__all__ = ['NetcdfFileReader']


class NetcdfFileReader(DataFileReader):
    @classmethod
    def read_data(cls, input_path: str) -> List[xr.Dataset]:

        # Specifying the engine is not strictly necessary since xarray
        # will determine the file type, but we want to use the grib implementation
        # for GRIB files, otherwise this code can fail in cryptic ways.
        # Explicitly setting the engine results in a clearer error.
        try:
            # Suppress the benign RuntimeWarning about numpy.ndarray size change
            # that can occur when importing the netCDF4 C extension compiled
            # against a different numpy ABI version.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="numpy.ndarray size changed",
                    category=RuntimeWarning,
                )
                ds = xr.open_dataset(input_path, engine='netcdf4')
        except OSError as ose:
            raise OSError(f'Unable to read file {input_path} as netcdf4') from ose
        return [ds]
