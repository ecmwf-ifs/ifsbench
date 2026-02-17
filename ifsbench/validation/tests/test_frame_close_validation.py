# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the :class:`FrameCloseValidation` implementation.
"""

import itertools
import logging

import json
from pathlib import Path

import pandas as pd
import pytest

from ifsbench.results import ResultData
from ifsbench.validation.frame_close_validation import (
    FrameCloseValidation,
    validate_result_identical,
)


@pytest.fixture(name="test_frames")
def build_frames():
    return [
        pd.DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]]),
        pd.DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=["Step 0", "Step 1"]),
        pd.DataFrame(
            [[2.0, 3.0, 4], [5.0, 1.0, 3]],
            index=["Step 0", "Step 1"],
            columns=["value1", "value2", "value3"],
        ),
        pd.DataFrame(
            [[2.0, 3.0, 4], [5.0, 1.0, 3]], columns=["value1", "value2", "value3"]
        ),
    ]


class TestResult(ResultData):
    pass


@pytest.mark.parametrize("atol", [0.0, 1e-4, 1])
@pytest.mark.parametrize("rtol", [0.0, 1e-4, 1])
def test_frameclose_equal_self(atol, rtol, test_frames):
    """
    Verify that a frame is always equal to itself.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    for frame in test_frames:
        equal, mismatch = validation.compare(frame, frame)

        assert equal
        assert len(mismatch) == 0


@pytest.mark.parametrize(
    "atol, rtol, add_noise",
    [
        (0, 0, 1e-4),
        (0, 0, 1),
        (1e-4, 0, -1e-3),
        (0, 1e-4, 1e-3),
    ],
)
def test_frameclose_unequal_self_noise(atol, rtol, add_noise, test_frames):
    """
    Verify that a frame is not equal to a perturbed copy of itself if the
    applied noise is larger than the tolerances.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    for frame in test_frames:
        frame2 = frame.copy()
        # Add noise only to float columns (i.e. exclude the last column).
        frame2.iloc[:, [0, 1]] += add_noise
        equal, mismatch = validation.compare(frame, frame2)
        assert not equal

        mismatch_ref = list(
            itertools.product(frame.index.values, frame.columns.values[:2])
        )

        assert mismatch == mismatch_ref


@pytest.mark.parametrize("atol", [0, 1e-8, 1e-4])
@pytest.mark.parametrize("rtol", [0, 1e-8, 1e-4])
def test_frameclose_explicit_mismatch(atol, rtol):
    """
    Some handcoded result checking for FrameCloseValidation.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    frame1 = pd.DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=["Step 0", "Step 1"])
    frame2 = pd.DataFrame([[2.0, 3.001, 4], [5.0, 1.0, 3]], index=["Step 0", "Step 1"])

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert mismatch == [("Step 0", 1)]


@pytest.mark.parametrize("atol", [0, 1e-8, 1e-4])
@pytest.mark.parametrize("rtol", [0, 1e-8, 1e-4])
def test_frameclose_explicit_mismatch_dtype(atol, rtol):
    """
    Some handcoded result checking for FrameCloseValidation.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    frame1 = pd.DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=["Step 0", "Step 1"])

    # Last column is treated as int. This shouldn't match frame1 due to this.
    frame2 = pd.DataFrame(
        [[2.0, 3.001, 4.0], [5.0, 1.0, 3]], index=["Step 0", "Step 1"]
    )

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal

    # No mismatch should be given as the general structure of the two frames
    # (datatypes!) is not equal.
    assert len(mismatch) == 0


@pytest.mark.parametrize("atol", [0, 1e-8, 1e-4])
@pytest.mark.parametrize("rtol", [0, 1e-8, 1e-4])
def test_frame_mismatch_multiindex(atol, rtol):
    """
    Some handcoded checks for multi-index frames and corresponding mismatch
    return values.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    index = pd.MultiIndex.from_tuples([("Step 0", "type a"), ("Step 0", "type b")])

    frame1 = pd.DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=index)
    frame2 = pd.DataFrame([[2.0, 3.001, 4], [5.0, 1.0, 3]], index=index)

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert mismatch == [(("Step 0", "type a"), 1)]
    assert frame1.loc[mismatch[0][0], mismatch[0][1]] == 3.0
    assert frame2.loc[mismatch[0][0], mismatch[0][1]] == 3.001


def test_validate_result_from_result(tmp_path, test_frames):
    ref_path = tmp_path / "ref_result.json"
    ref_result = TestResult(frames={"frame1": test_frames[0], "frame2": test_frames[1]})
    with ref_path.open("w") as f:
        json.dump(ref_result.dump_config(), f)

    test_result = TestResult(
        frames={"frame1": test_frames[0], "frame2": test_frames[1]}
    )

    assert validate_result_identical(test_result, Path(ref_path), TestResult) is True


def test_validate_result_from_file(tmp_path, test_frames):
    ref_path = tmp_path / "ref_result.json"
    ref_result = TestResult(frames={"frame1": test_frames[0], "frame2": test_frames[1]})
    with ref_path.open("w") as f:
        json.dump(ref_result.dump_config(), f)

    result_path = tmp_path / "result.json"
    test_result = TestResult(
        frames={"frame1": test_frames[0], "frame2": test_frames[1]}
    )
    with result_path.open("w") as f:
        json.dump(test_result.dump_config(), f)

    validate_result_identical(result_path, Path(ref_path), TestResult)


def test_validate_result_from_result_wrongtype_fails(tmp_path, test_frames):
    class AnotherResult(ResultData):
        pass

    ref_path = tmp_path / "ref_result.json"
    ref_result = TestResult(frames={"frame1": test_frames[0], "frame2": test_frames[1]})
    with ref_path.open("w") as f:
        json.dump(ref_result.dump_config(), f)

    test_result = AnotherResult(
        frames={"frame1": test_frames[0], "frame2": test_frames[1]}
    )

    with pytest.raises(RuntimeError) as exceptinfo:
        validate_result_identical(test_result, Path(ref_path), TestResult)

    assert "Result is of wrong type, expected" in str(exceptinfo.value)
    assert "found" in str(exceptinfo.value)


def test_validate_result_not_equal(tmp_path, caplog, test_frames):
    logging.getLogger("ifsbench").setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    added_row = pd.DataFrame([[7.0, 8.0, 9]], index=[2])
    mod_frame = pd.concat([test_frames[0], added_row])

    ref_path = tmp_path / "ref_result.json"
    ref_result = TestResult(
        frames={
            "frame1": test_frames[0],
        }
    )
    with ref_path.open("w") as f:
        json.dump(ref_result.dump_config(), f)

    test_result = TestResult(
        frames={
            "frame1": mod_frame,
        }
    )

    assert validate_result_identical(test_result, Path(ref_path), TestResult) is False

    not_equal_log = "Frames are not equal:\nshapes: result=(3, 3), ref=(2, 3)\nindex"

    assert any(not_equal_log in message for message in caplog.messages)


def test_validate_result_mismatch(tmp_path, caplog, test_frames):
    logging.getLogger("ifsbench").setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    mismatched_frame = test_frames[1] + 1

    ref_path = tmp_path / "ref_result.json"
    ref_result = TestResult(frames={"frame1": test_frames[0], "frame2": test_frames[1]})
    with ref_path.open("w") as f:
        json.dump(ref_result.dump_config(), f)

    test_result = TestResult(
        frames={"frame1": test_frames[0], "frame2": mismatched_frame}
    )

    assert validate_result_identical(test_result, Path(ref_path), TestResult) is False

    result_data_log = (
        "result data:\n          0    1  2\nStep 0  3.0  4.0  5\nStep 1  6.0  2.0  4"
    )
    reference_data_log = (
        "reference data:\n          0    1  2\nStep 0  2.0  3.0  4\nStep 1  5.0  1.0  3"
    )
    mismatch_log = "First mismatch at (Step 0, 0): 3.0 != 2.0."

    assert result_data_log in caplog.messages
    assert reference_data_log in caplog.messages
    assert mismatch_log in caplog.messages
