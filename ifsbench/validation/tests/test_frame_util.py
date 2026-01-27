# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the DataFrame utility functions.
"""

from pandas import DataFrame, Index
import pytest

from ifsbench.validation.frame_util import get_float_columns, get_int_columns


@pytest.mark.parametrize(
    "frame, col_out",
    [
        (DataFrame(), []),
        (DataFrame([[1]]), []),
        (DataFrame([[1.0]]), [0]),
        (DataFrame([[1.0]], columns=["first"]), ["first"]),
        (DataFrame([[1.0, 2], [3.5, 2]], columns=["first", "second"]), ["first"]),
        (DataFrame([[1.0, 2], [3, 2.1]]), [0, 1]),
    ],
)
def test_get_float_columns(frame, col_out):
    """
    Test that get_float_columns returns the correct columns.
    """
    subframe = get_float_columns(frame)

    col_out = Index(col_out)
    assert subframe.columns.equals(col_out)


@pytest.mark.parametrize(
    "frame, col_out",
    [
        (DataFrame(), []),
        (DataFrame([[1]]), [0]),
        (DataFrame([[1.0]]), []),
        (DataFrame([[1]], columns=["first"]), ["first"]),
        (DataFrame([[1.0, 2], [3.5, 2]], columns=["first", "second"]), ["second"]),
        (DataFrame([[1, 2], [3, 2]]), [0, 1]),
    ],
)
def test_get_int_columns(frame, col_out):
    """
    Test that get_int_columns returns the correct columns.
    """
    subframe = get_int_columns(frame)

    col_out = Index(col_out)
    assert subframe.columns.equals(col_out)
