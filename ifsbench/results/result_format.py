# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Dict, Optional

from ifsbench import PydanticDataFrame
from ifsbench.serialisation_mixin import SerialisationMixin

__all__ = ["ResultData", "ResultInfo"]


class ResultData(SerialisationMixin):
    """
    Generic result class that can be serialised and validated using existing tools.
    """

    #: Numerical results of the run, stored as DataFrames (with corresponding
    #: file name).
    frames: Dict[str, PydanticDataFrame]


class ResultInfo(ResultData):
    """
    Generic result class with data and additional information.
    """

    #: Standard out of the run.
    stdout: Optional[str] = None

    #: Standard error of the run.
    stderr: Optional[str] = None

    #: Walltime of the run in seconds.
    walltime: Optional[float] = None
