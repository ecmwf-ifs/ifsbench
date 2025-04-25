# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from dataclasses import dataclass
from typing import Any, List, Tuple

import numpy
from pandas import DataFrame

from ifsbench.validation.frame_util import get_float_columns

@dataclass
class FrameCloseValidation:
    """
    Compare pandas.DataFrame using numpy.isclose.

    This class can be used to compare two dataframes for near equality.
    The used comparison approach is as follows:

    * both frames are stripped of their non-float columns.
    * numpy.isclose is used to compare the float values, using given
      absolute and relative tolerances.
    """

    #: The absolute tolerance that is used.
    atol: float = 0

    #: The relative tolerance that is used.
    rtol: float = 0

    def compare(self,
        frame1: DataFrame,
        frame2: DataFrame
    ) -> Tuple[bool, List[Tuple[Any, Any]]]:
        """
        Compare two dataframes.

        Parameters
        ----------
        frame1: pandas.DataFrame
          The first dataframe.
        frame2: pandas.DataFrame
          The second dataframe.

        Returns
        -------
        bool:
          Whether or not the two frames are equal up to the given tolerances.
        List[Tuple[Any, Any]]:
          List of (index, column) pairs that indicate all positions where the frames
          are not close.
          If the two frames have different indices, columns or different data types 
          an empty list is returned.
        """

        frame1 = get_float_columns(frame1)
        frame2 = get_float_columns(frame2)

        if not frame1.index.equals(frame2.index):
            return False, []

        if not frame1.columns.equals(frame2.columns):
            return False, []

        close = numpy.isclose(frame1.values, frame2.values, rtol=self.rtol, atol=self.atol, equal_nan=True)

        mismatch = numpy.argwhere(~close)
        mismatch = [(frame1.index[i], frame1.columns[j]) for i,j in mismatch]

        return numpy.all(close), mismatch
        