# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from typing import List

import xarray as xr

__all__ = ["DataFileReader"]


class DataFileReader(ABC):
    """Interface for reading data.

    Each implementation support a different file format.
    """

    @classmethod
    @abstractmethod
    def read_data(cls, input_path: str) -> List[xr.Dataset]:
        """Open data file and parse into datasets.

        Args:
            input_path: data file to read

        Returns:
            List of xarray Datasets containing the data in the file.
        """
        raise NotImplementedError()
