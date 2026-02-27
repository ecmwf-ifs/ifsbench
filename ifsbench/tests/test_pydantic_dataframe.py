# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Check the PydandictDataFrame type.
"""

import json
from typing import Dict, List

from pandas import DataFrame, MultiIndex, Timestamp
import pytest
import yaml

from ifsbench import SerialisationMixin, PydanticDataFrame


class _PydanticDataFrameTest(SerialisationMixin):
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
        frame_list=[default_frames[2]],
    )

    assert obj.frame.equals(default_frames[0])
    assert obj.frame_dict['name'].equals(default_frames[1])
    assert obj.frame_list[0].equals(default_frames[2])


class _DummyClass(SerialisationMixin):
    frame: PydanticDataFrame


def test_pydantic_data_to_config():
    """
    Serialise PydanticFrame objects and check the serialisation output.
    """

    frame = DataFrame([[2.0, 3.0, 1.0]], index=['First index'], columns=['mean', 'max', 'min'])

    obj = _DummyClass(frame=frame)

    config = obj.dump_config()
    ref = {
        'frame': {
            'index': ['First index'],
            'columns': ['mean', 'max', 'min'],
            'data': [[2.0, 3.0, 1.0]],
            'index_names': [None],
            'column_names': [None],
        }
    }

    assert config == ref


def test_pydantic_data_to_config_multiindex():
    """
    Serialise PydanticFrame objects and check the serialisation output.
    """

    index = MultiIndex.from_tuples(
        [
            ('min', 'soil stuff'),
            ('mean', 'soil stuff'),
            ('min', 'water stuff'),
            ('mean', 'water stuff'),
        ],
        names=['stat', 'type'],
    )

    frame = DataFrame(
        [[2.0, 3.0, 1.0], [4.0, -2.0, 1.0], [0.0, 0.0, 5.0], [2.0, 3.0, 4.0]],
        index=index,
        columns=['mean', 'max', 'min'],
    )

    obj = _DummyClass(frame=frame)

    config = obj.dump_config()
    ref = {
        'frame': {
            'index': [
                ['min', 'soil stuff'],
                ['mean', 'soil stuff'],
                ['min', 'water stuff'],
                ['mean', 'water stuff'],
            ],
            'columns': ['mean', 'max', 'min'],
            'data': [[2.0, 3.0, 1.0], [4.0, -2.0, 1.0], [0.0, 0.0, 5.0], [2.0, 3.0, 4.0]],
            'index_names': ['stat', 'type'],
            'column_names': [None],
        }
    }

    assert config == ref


def test_pydantic_data_from_config_python(default_frames):
    """
    Check the from_config functionality, by
        * serialising an object with dump_config
        * call from_config to restore the original object
        * check that the original and recovered object are equal.
    """

    obj = _PydanticDataFrameTest(
        frame=default_frames[0],
        frame_dict={'name': default_frames[1]},
        frame_list=[default_frames[2]],
    )

    config = obj.dump_config()

    copy = _PydanticDataFrameTest.from_config(config)

    assert obj.frame.equals(copy.frame)

    assert len(obj.frame_dict) == len(copy.frame_dict)
    assert len(obj.frame_list) == len(copy.frame_list)

    assert obj.frame_dict['name'].equals(copy.frame_dict['name'])
    assert obj.frame_list[0].equals(copy.frame_list[0])


def test_pydantic_data_from_config_json(tmp_path, default_frames):
    """
    Check the from_config functionality, by
        * serialising an object with dump_config
        * writing the resulting dict to JSON
        * re-read from the JSON file
        * call from_config to restore the original object
        * check that the original and recovered object are equal.
    """

    obj = _PydanticDataFrameTest(
        frame=default_frames[0],
        frame_dict={'name': default_frames[1]},
        frame_list=[default_frames[2]],
    )

    config = obj.dump_config()

    path = tmp_path / 'file.json'

    with path.open('w') as f:
        json.dump(config, f)
    with path.open('r') as f:
        data = json.load(f)

    copy = _PydanticDataFrameTest.from_config(data)

    assert obj.frame.equals(copy.frame)

    assert len(obj.frame_dict) == len(copy.frame_dict)
    assert len(obj.frame_list) == len(copy.frame_list)

    assert obj.frame_dict['name'].equals(copy.frame_dict['name'])
    assert obj.frame_list[0].equals(copy.frame_list[0])


def test_pydantic_data_from_config_yaml(tmp_path, default_frames):
    """
    Check the from_config functionality, by
        * serialising an object with dump_config
        * writing the resulting dict to YAML
        * re-read from the YAML file
        * call from_config to restore the original object
        * check that the original and recovered object are equal.
    """

    obj = _PydanticDataFrameTest(
        frame=default_frames[0],
        frame_dict={'name': default_frames[1]},
        frame_list=[default_frames[2]],
    )

    config = obj.dump_config()

    path = tmp_path / 'file.yaml'

    with path.open('w') as f:
        yaml.dump(config, f)
    with path.open('r') as f:
        data = yaml.safe_load(f)

    copy = _PydanticDataFrameTest.from_config(data)

    assert obj.frame.equals(copy.frame)

    assert len(obj.frame_dict) == len(copy.frame_dict)
    assert len(obj.frame_list) == len(copy.frame_list)

    assert obj.frame_dict['name'].equals(copy.frame_dict['name'])
    assert obj.frame_list[0].equals(copy.frame_list[0])


@pytest.mark.parametrize(
    'frame',
    [
        DataFrame([[2.0, 3.0, 1.0]], index=['First index'], columns=['mean', 'max', 'min']),
        DataFrame(),
        DataFrame([[1.0], [0.0]]),
        DataFrame(
            [
                [5.0, 2.0, 4.0, Timestamp(year=2023, day=12, month=11)],
                [6.0, 1.0, 2.0, Timestamp(year=1991, day=5, month=2)],
            ],
            columns=['b', 'a', 'c', 'time'],
            index=MultiIndex.from_product(
                [(Timestamp(year=2000, day=1, month=4),), ('Step 0', 'Step 1')]
            ),
        ),
    ],
)
def test_pydantic_data_frame_equal(frame):
    """
    Check the serialisation/deserialisation of a data frame yields equal data
    frames.
    """

    obj = _DummyClass(frame=frame)

    config = obj.dump_config()
    obj_clone = _DummyClass.from_config(config)

    assert obj.frame.equals(obj_clone.frame)


def test_pydantic_data_frame_serialise_timestamp():
    """
    Check the serialisation of a data frame if it contains pandas.Timestamp objects.
    """

    timestamp = Timestamp(year=2024, day=24, month=6)
    frame = DataFrame(
        [[5.0, 2.0, 4.0, timestamp], [6.0, 1.0, 2.0, timestamp]],
        columns=['b', 'a', 'c', 'time'],
        index=MultiIndex.from_product([(timestamp,), ('Step 0', 'Step 1')]),
    )

    obj = _DummyClass(frame=frame)

    config = obj.dump_config()

    ref = {
        'frame': {
            'index': [
                ['2024-06-24T00:00:00_pd_timestamp', 'Step 0'],
                ['2024-06-24T00:00:00_pd_timestamp', 'Step 1'],
            ],
            'columns': ['b', 'a', 'c', 'time'],
            'data': [
                [5.0, 2.0, 4.0, '2024-06-24T00:00:00_pd_timestamp'],
                [6.0, 1.0, 2.0, '2024-06-24T00:00:00_pd_timestamp'],
            ],
            'index_names': [None, None],
            'column_names': [None],
        }
    }

    assert config == ref
