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

from pandas import DataFrame, MultiIndex
import pytest

from ifsbench.validation.frame_close_validation import FrameCloseValidation

@pytest.fixture(name='test_frames')
def build_frames():
    return [
        DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]]),
        DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=['Step 0', 'Step 1']),
        DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=['Step 0', 'Step 1'], columns=['value1', 'value2', 'value3']),
        DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], columns=['value1', 'value2', 'value3']),
    ]

@pytest.mark.parametrize('atol', [0.0, 1e-4, 1])
@pytest.mark.parametrize('rtol', [0.0, 1e-4, 1])
def test_frameclose_equal_self(atol, rtol, test_frames):
    """
    Verify that a frame is always equal to itself.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    for frame in test_frames:
        equal, mismatch = validation.compare(frame, frame)

        assert equal
        assert len(mismatch) == 0

@pytest.mark.parametrize('atol, rtol, add_noise',[
    (0, 0, 1e-4), (0, 0, 1),
    (1e-4, 0, -1e-3), (0, 1e-4, 1e-3),
])
def test_frameclose_unequal_self_noise(atol, rtol, add_noise, test_frames):
    """
    Verify that a frame is not equal to a perturbed copy of itself if the 
    applied noise is larger than the tolerances.
    """
    validation = FrameCloseValidation(atol=atol, rtol=rtol)

    for frame in test_frames:
        frame2 = frame.copy()
        # Add noise only to float columns (i.e. exclude the last column).
        frame2.iloc[:, [0,1]] += add_noise
        equal, mismatch = validation.compare(frame, frame2)
        assert not equal

        mismatch_ref = list(itertools.product(frame.index.values, frame.columns.values[:2]))

        assert mismatch == mismatch_ref


def test_frameclose_explicit():
    """
    Some handcoded result checking for FrameCloseValidation.
    """
    validation = FrameCloseValidation(atol=0, rtol=0)

    frame1 = DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=['Step 0', 'Step 1'])
    frame2 = DataFrame([[2.0, 3.001, 4], [5.0, 1.0, 3]], index=['Step 0', 'Step 1'])

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert mismatch == [('Step 0', 1)]

    frame2 = DataFrame([[2.0, 3.001, 4.0], [5.0, 1.0, 3]], index=['Step 0', 'Step 1'])

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert len(mismatch) == 0


def test_frame_mismatch_multiindex():
    """
    Some handcoded checks for multi-index frames and corresponding mismatch
    return values.
    """
    validation = FrameCloseValidation(atol=0, rtol=0)

    index = MultiIndex.from_tuples([('Step 0', 'type a'), ('Step 0', 'type b')])

    frame1 = DataFrame([[2.0, 3.0, 4], [5.0, 1.0, 3]], index=index)
    frame2 = DataFrame([[2.0, 3.001, 4], [5.0, 1.0, 3]], index=index)

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert mismatch == [(('Step 0', 'type a'), 1)]
    assert frame1.loc[mismatch[0][0], mismatch[0][1]] == 3.0
    assert frame2.loc[mismatch[0][0], mismatch[0][1]] == 3.001

    frame2 = DataFrame([[2.0, 3.001, 4.0], [5.0, 1.0, 3]], index=['Step 0', 'Step 1'])

    equal, mismatch = validation.compare(frame1, frame2)

    assert not equal
    assert len(mismatch) == 0
