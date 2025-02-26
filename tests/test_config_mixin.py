# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import Dict, List

import pytest
from pydantic import ValidationError

from ifsbench import PydanticConfigMixin


class TestImpl(PydanticConfigMixin):
    field_str: str
    field_int: int
    field_list: List[Dict[str, str]]
    field_path: Path


def test_from_config_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
        'field_path': 'some/where',
    }
    ti = TestImpl.from_config(config)

    assert ti.field_str == 'val_str'
    assert ti.field_path == Path('some/where')


def test_from_config_path_object_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
        'field_path': Path('some/where'),
    }
    ti = TestImpl.from_config(config)

    assert ti.field_str == 'val_str'
    assert ti.field_path == Path('some/where')


def test_from_config_invalid_fails():

    config = {
        'field_str': 999.0,
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
        'field_path': 'some/where',
    }
    with pytest.raises(ValidationError):
        TestImpl.from_config(config)


def test_dumb_config_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
        'field_path': 'some/where',
    }
    ti = TestImpl.from_config(config)

    assert ti.dump_config() == config


def test_dumb_config_with_class_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
        'field_path': 'some/where',
    }
    ti = TestImpl.from_config(config)

    expected = config.copy()
    expected['classname'] = 'TestImpl'
    assert ti.dump_config(with_class=True) == expected


def test_from_config_invalid_class_member_fails():

    class TestInvalidImpl(PydanticConfigMixin):
        classname: str
        field_int: int
        field_list: List[Dict[str, str]]

    config = {
        'classname': 'clz',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }

    with pytest.raises(ValidationError) as exceptinfo:
        TestInvalidImpl(**config)
    expected = 'Value error, Invalid ConfigMixin class: contains reserved member name(s). Reserved:'

    assert expected in str(exceptinfo.value)
