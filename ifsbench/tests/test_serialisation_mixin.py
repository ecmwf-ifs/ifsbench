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

from ifsbench import SerialisationMixin, SubclassableSerialisationMixin, CLASSNAME


class TestImpl(SerialisationMixin):
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
    expected[CLASSNAME] = 'TestImpl'
    assert ti.dump_config(with_class=True) == expected


class SecondBaseClass(SubclassableSerialisationMixin):
    str_value: str


class SecondChildClass(SecondBaseClass):
    bool_value: bool


class TestBase(SubclassableSerialisationMixin):
    float_value: float


class TestChild1(TestBase):
    list_str: List[str]


class TestChild2(TestBase):
    first_int: int
    second_int: int
    child: SecondBaseClass


class TestCombine(SerialisationMixin):
    child: TestBase


def test_subclass_serialisation():
    """
    Test that subclasses serialise properly.
    """

    obj = TestCombine(child=TestChild1(list_str=['Hello', 'world'], float_value=4.5))

    config = obj.dump_config()

    assert config == {
        'child': {'class_name': 'TestChild1', 'list_str': ['Hello', 'world'], 'float_value': 4.5}
    }

    obj = TestCombine(
        child=TestChild2(
            first_int=5,
            second_int=6,
            float_value=2.1,
            child=SecondChildClass(bool_value=False, str_value='hello'),
        )
    )

    config = obj.dump_config()

    assert config == {
        'child': {
            'class_name': 'TestChild2',
            'first_int': 5,
            'second_int': 6,
            'float_value': 2.1,
            'child': {'class_name': 'SecondChildClass', 'bool_value': False, 'str_value': 'hello'},
        }
    }
