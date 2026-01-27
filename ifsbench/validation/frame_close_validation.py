# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Tuple, Type, Union

import numpy
from pandas import DataFrame
import yaml

from ifsbench.logging import debug, error, info
from ifsbench.results import ResultData
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

    def compare(
        self, frame1: DataFrame, frame2: DataFrame
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

        close = numpy.isclose(
            frame1.values, frame2.values, rtol=self.rtol, atol=self.atol, equal_nan=True
        )

        mismatch = numpy.argwhere(~close)
        mismatch = [(frame1.index[i], frame1.columns[j]) for i, j in mismatch]

        return numpy.all(close), mismatch


def validate_result_identical(
    result: Union[str, Path, ResultData],
    reference_path: Path,
    result_type: Type[ResultData],
    atol: float = 0,
    rtol: float = 0,
) -> bool:
    """
    Compare result to reference to check if they are within specified tolerances.

    Parameters
    ----------
    result: str or path to file holding result, or ifsbench.results.ResultData
      The result data to compare.
    reference_path: pathlib.Path
      The reference data file to which to compare the result.
    result_type: Type[ResultData]
      The specific class of ResultData used to read the reference data
    atol: float
      The absolute tolerance when comparing data values.
    rtol: float
      The relative tolerance when comparing data values.

    Returns
    -------
    bool:
      Whether or not the two frames are equal up to the given tolerances.
    """

    validator = FrameCloseValidation(atol, rtol)

    if isinstance(result, (str, Path)):
        with Path(result).open("r", encoding="utf-8") as f:
            result_data = result_type.from_config(yaml.safe_load(f))
    elif isinstance(result, result_type):
        result_data = result
    else:
        raise RuntimeError(
            f"Result is of wrong type, expected {result_type}, found {type(result)}"
        )

    with Path(reference_path).open("r", encoding="utf-8") as f:
        reference_data = result_type.from_config(yaml.safe_load(f))

    info(f"Validating result type {result_type} against {reference_path}")
    if set(result_data.frames.keys()) != set(reference_data.frames.keys()):
        raise RuntimeError("Results do not hold the same frames!")
    is_identical = True

    for key in result_data.frames.keys():
        frame = result_data.frames[key]
        frame_ref = reference_data.frames[key]

        equal, mismatch = validator.compare(frame, frame_ref)
        if not equal and mismatch:
            is_identical = False
            idx, col = mismatch[0]
            error(
                f"First mismatch at ({idx}, {col}): {frame.loc[idx,col]} != {frame_ref.loc[idx,col]}."
            )

            for idx, col in mismatch:
                debug(
                    f"Mismatch at ({idx}, {col}): {frame.loc[idx,col]} != {frame_ref.loc[idx,col]}."
                )
    return is_identical
