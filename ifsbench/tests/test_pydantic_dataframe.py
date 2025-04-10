# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Check the PydandictDataFrame type.
"""

from typing import Dict, List

from pandas import DataFrame
import pytest

from ifsbench import PydanticConfigMixin, PydanticDataFrame

class _PydanticDataFrameTest(PydanticConfigMixin):
    """
    Simple pydantic object that includes PydatanticDataFrame in different ways.
    """
    frame: PydanticDataFrame

    frame_dict: Dict[str, PydanticDataFrame]
    frame_list: List[PydanticDataFrame]

@pytest.fixture(name='default_frames')
def fixture_default_frames():
    frame1 = DataFrame([[1.0, 2.0], [3.0, 4.0]])
    frame2 = DataFrame([[0.0, -2.0]], index=['Some index'])
    frame3 = DataFrame([[5.0, 2.0, 4.0], [6.0, 1.0, 2.0]], columns=['b', 'a', 'c'])

    return frame1, frame2, frame3


def test_pydantic_data_frame_init(default_frames):
    """
    Check that we can initialise an object that uses PydanticDataFrame and that
    the stored frames are equal to the initial frames.
    """
    obj = _PydanticDataFrameTest(
        frame=default_frames[0],
        frame_dict={'name': default_frames[1]},
        frame_list=[default_frames[2]]
    )

    assert obj.frame.equals(default_frames[0])
    assert obj.frame_dict['name'].equals(default_frames[1])
    assert obj.frame_list[0].equals(default_frames[2])


def test_pydantic_data_frame_recover(default_frames):
    """
    Serialise and deserialise PydanticFrame objects and check that they are the
    same after serialisation.
    """
    obj = _PydanticDataFrameTest(
        frame=default_frames[0],
        frame_dict={'name': default_frames[1]},
        frame_list=[default_frames[2]]
    )

    config = obj.dump_config()

    copy = _PydanticDataFrameTest.from_config(config)

    assert obj.frame.equals(copy.frame)

    assert len(obj.frame_dict) == len(copy.frame_dict)
    assert len(obj.frame_list) == len(copy.frame_list)

    assert obj.frame_dict['name'].equals(copy.frame_dict['name'])
    assert obj.frame_list[0].equals(copy.frame_list[0])
