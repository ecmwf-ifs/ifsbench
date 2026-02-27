# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for handling namelists
"""

from pathlib import Path
import tempfile

import f90nml
import pytest

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict
from ifsbench import sanitise_namelist, namelist_diff, IFSNamelist


@pytest.fixture(scope='module', name='here')
def fixture_here():
    return Path(__file__).parent


def available_modes(xfail=None, skip=None):
    """
    Provide list of available modes to parametrize tests with

    Parameters
    ----------
    xfail : list, optional
        Provide frontends that are expected to fail, optionally as tuple with reason
        provided as string. By default `None`
    skip : list, optional
        Provide frontends that are always skipped, optionally as tuple with reason
        provided as string. By default `None`
    """
    modes = ['auto', 'legacy', 'f90nml']
    if xfail:
        xfail = dict((tuple(m) + (None,))[:2] for m in xfail)
    else:
        xfail = {}

    if skip:
        skip = dict((tuple(m) + (None,))[:2] for m in skip)
    else:
        skip = {}

    # Build the list of parameters
    params = []
    for m in modes:
        if m in skip:
            params += [pytest.param(m, marks=pytest.mark.skip(reason=skip[m]))]
        elif m in xfail:
            params += [pytest.param(m, marks=pytest.mark.xfail(reason=xfail[m]))]
        else:
            params += [m]

    return params


@pytest.mark.parametrize('mode', available_modes())
def test_sanitise_namelist(mode):
    nml_string = """
&a
    foo = 4
    foobar = 3
/
&b
    bar = 1
    foo = 2
/
&a
    foo = 1
    bar = 2
/
    """.strip()

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        nml_file = Path(tmp_dir) / 'nml'
        with nml_file.open('w') as f:
            f.write(nml_string)
        nml = f90nml.read(nml_file)

    sanitised = sanitise_namelist(nml, merge_strategy='first', mode=mode)
    assert sanitised.todict() == {'a': {'foo': 4, 'foobar': 3}, 'b': {'bar': 1, 'foo': 2}}

    sanitised = sanitise_namelist(nml, merge_strategy='last', mode=mode)
    assert sanitised.todict() == {'a': {'foo': 1, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}

    sanitised = sanitise_namelist(nml, merge_strategy='merge_first', mode=mode)
    assert sanitised.todict() == {'a': {'foo': 4, 'foobar': 3, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}

    sanitised = sanitise_namelist(nml, merge_strategy='merge_last', mode=mode)
    assert sanitised.todict() == {'a': {'foo': 1, 'foobar': 3, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}


def test_empty_namelist():
    nml_string = """
&a
    foo = 4
    foobar = 3
/
&b
    bar = 1
    foo = 2
/
&a
    foo = 1
    bar = 2
/
&a
/
&c
/
    """.strip()
    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        nml_file = Path(tmp_dir) / 'nml'
        nml_file.write_text(nml_string)
        nml = f90nml.read(nml_file)

    sanitised = sanitise_namelist(nml, merge_strategy='first')
    assert sanitised.todict() == {'a': {'foo': 4, 'foobar': 3}, 'b': {'bar': 1, 'foo': 2}, 'c': {}}

    sanitised = sanitise_namelist(nml, merge_strategy='last')
    assert sanitised.todict() == {'a': {}, 'b': {'bar': 1, 'foo': 2}, 'c': {}}

    sanitised = sanitise_namelist(nml, merge_strategy='merge_first')
    assert sanitised.todict() == {
        'a': {'foo': 4, 'foobar': 3, 'bar': 2},
        'b': {'bar': 1, 'foo': 2},
        'c': {},
    }

    sanitised = sanitise_namelist(nml, merge_strategy='merge_last')
    assert sanitised.todict() == {
        'a': {'foo': 1, 'foobar': 3, 'bar': 2},
        'b': {'bar': 1, 'foo': 2},
        'c': {},
    }


def test_namelist_diff():
    nml1_string = """
&a
    foo = 1
    bar = 2
/
&b
    bar = 1
    foo = 2
/
    """.strip()
    nml2_string = """
&a
    bar = 2
    foo = 1
/
&b
    foo = 2
    bar = 1
/
    """.strip()
    nml3_string = """
&a
    bar = 1
    foobar = 3
/
&c
    foofoo = 4
/
    """.strip()

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        nml1_file = Path(tmp_dir) / 'nml1'
        with nml1_file.open('w') as f:
            f.write(nml1_string)
        nml1 = f90nml.read(nml1_file)

        nml2_file = Path(tmp_dir) / 'nml2'
        with nml2_file.open('w') as f:
            f.write(nml2_string)
        nml2 = f90nml.read(nml2_file)

        nml3_file = Path(tmp_dir) / 'nml3'
        with nml3_file.open('w') as f:
            f.write(nml3_string)
        nml3 = f90nml.read(nml3_file)

    assert not namelist_diff(nml1, nml1.copy())
    assert not namelist_diff(nml1, nml2)
    assert namelist_diff(nml1, nml3) == {
        'a': {
            'foo': (1, None),
            'bar': (2, 1),
            'foobar': (None, 3),
        },
        'b': ({'bar': 1, 'foo': 2}, None),
        'c': (None, {'foofoo': 4}),
    }


def convert(_nml):
    """
    convert relevant keys to original layout ...
    """
    # Convert to f90nml<1.4 format
    nml = f90nml.Namelist()
    for key_, values in _nml.items():
        key = str(key_)
        if key in nml:
            if isinstance(nml[key], list):
                nml[key] += [values]
            else:
                nml[key] = [nml[key], values]
        else:
            nml[key] = values
    for key in nml:
        if isinstance(nml[key], list):
            _ = []
            for i in range(len(nml[key])):
                _.extend(
                    [_key for _key in nml[key][i] if isinstance(nml[key][i][_key], f90nml.Namelist)]
                )
            if len(set(_)) == 1:
                content = []
                for values in nml[key]:
                    if _[0] in values:
                        content.append(values[_[0]])
                    merged = f90nml.Namelist({key: content})
                    nml[key] = merged
    return nml


@pytest.mark.parametrize('mode', available_modes())
def test_namelist_duplicate_key(here, mode):

    nml_template = here / 'namelists/template.nml'
    nml_file_1 = here / 'namelists/array_1.nml'
    nml_file_2 = here / 'namelists/array_2.nml'

    nml_1 = IFSNamelist(namelist=nml_file_1, template=nml_template, mode=mode)
    nml_2 = IFSNamelist(namelist=nml_file_2, template=nml_template, mode=mode)

    _val = OrderedDict([('val', 42)])
    _somearray_1 = OrderedDict([('a', '1string'), ('b', '1thing'), ('c', 1), ('d', -1.0)])
    _somearray_2 = OrderedDict([('a', '2string'), ('b', '2thing'), ('c', 2), ('d', -2.0)])
    _somearray_3 = OrderedDict([('a', '3string'), ('b', '3thing'), ('c', 3), ('d', -3.0)])
    _another_array_1 = OrderedDict([('e', 'another1string'), ('f', 'another1thing')])
    _another_array_2 = OrderedDict([('e', 'another2string'), ('f', 'another2thing')])

    if mode == 'legacy':
        assert nml_1.nml.todict() == OrderedDict(
            [
                ('someval', _val),
                (
                    'somearray',
                    OrderedDict(
                        [
                            ('somearray', [_somearray_1, _somearray_2, _somearray_3]),
                            ('_start_index', {'somearray': [1]}),
                        ]
                    ),
                ),
                (
                    'anotherarray',
                    OrderedDict(
                        [
                            ('anotherarray', [_another_array_1, _another_array_2]),
                            ('_start_index', {'anotherarray': [1]}),
                        ]
                    ),
                ),
            ]
        )
        assert nml_2.nml.todict() == OrderedDict(
            [
                ('someval', _val),
                ('somearray', OrderedDict([('this', _somearray_1)])),
                ('anotherarray', OrderedDict([('self', _another_array_1)])),
            ]
        )

        assert nml_1.nml != nml_2.nml
        assert nml_1.nml['someval'] == nml_2.nml['someval']
        assert nml_1.nml['somearray'] != nml_2.nml['somearray']
        assert nml_1.nml['anotherarray'] != nml_2.nml['anotherarray']

    elif mode == 'auto':
        assert nml_1.nml.todict() == OrderedDict(
            [
                ('someval', _val),
                (
                    'somearray',
                    OrderedDict(
                        [
                            ('somearray', [_somearray_1, _somearray_2, _somearray_3]),
                            ('_start_index', {'somearray': [1]}),
                        ]
                    ),
                ),
                (
                    'anotherarray',
                    OrderedDict(
                        [
                            ('anotherarray', [_another_array_1, _another_array_2]),
                            ('_start_index', {'anotherarray': [1]}),
                        ]
                    ),
                ),
            ]
        )
        assert nml_2.nml.todict() == OrderedDict(
            [
                ('someval', _val),
                ('somearray', OrderedDict()),
                ('anotherarray', OrderedDict()),
                ('_grp_somearray_0', OrderedDict([('this', _somearray_1)])),
                ('_grp_somearray_1', OrderedDict([('this', _somearray_2)])),
                ('_grp_somearray_2', OrderedDict([('this', _somearray_3)])),
                ('_grp_somearray_3', OrderedDict()),
                ('_grp_anotherarray_0', OrderedDict([('self', _another_array_1)])),
                ('_grp_anotherarray_1', OrderedDict([('self', _another_array_2)])),
                ('_grp_anotherarray_2', OrderedDict()),
            ]
        )

        _converted_nml_2 = convert(nml_2.nml)
        assert nml_1.nml == _converted_nml_2

    elif mode == 'f90nml':
        assert nml_1.nml.todict() == OrderedDict(
            [
                ('someval', OrderedDict()),
                (
                    'somearray',
                    OrderedDict(
                        [
                            ('somearray', [_somearray_1, _somearray_2, _somearray_3]),
                            ('_start_index', {'somearray': [1]}),
                        ]
                    ),
                ),
                (
                    'anotherarray',
                    OrderedDict(
                        [
                            ('anotherarray', [_another_array_1, _another_array_2]),
                            ('_start_index', {'anotherarray': [1]}),
                        ]
                    ),
                ),
                ('_grp_someval_0', _val),
                ('_grp_someval_1', _val),
            ]
        )

        assert nml_2.nml.todict() == OrderedDict(
            [
                ('someval', OrderedDict()),
                ('somearray', OrderedDict()),
                ('anotherarray', OrderedDict()),
                ('_grp_someval_0', _val),
                ('_grp_someval_1', _val),
                ('_grp_somearray_0', OrderedDict([('this', _somearray_1)])),
                ('_grp_somearray_1', OrderedDict([('this', _somearray_2)])),
                ('_grp_somearray_2', OrderedDict([('this', _somearray_3)])),
                ('_grp_somearray_3', OrderedDict()),
                ('_grp_anotherarray_0', OrderedDict([('self', _another_array_1)])),
                ('_grp_anotherarray_1', OrderedDict([('self', _another_array_2)])),
                ('_grp_anotherarray_2', OrderedDict()),
            ]
        )

        _converted_nml_1 = convert(nml_1.nml)
        _converted_nml_2 = convert(nml_2.nml)
        assert _converted_nml_1 == _converted_nml_2


@pytest.mark.parametrize(
    'mode', available_modes(xfail=[('f90nml', 'nml["someval"] is a list as not sanitised')])
)
def test_namelist_duplicate_key_set_val(here, mode):

    nml_template = here / 'namelists/template.nml'
    nml_file_1 = here / 'namelists/array_1.nml'
    nml_file_2 = here / 'namelists/array_2.nml'

    nml_1 = IFSNamelist(namelist=nml_file_1, template=nml_template, mode=mode)
    nml_2 = IFSNamelist(namelist=nml_file_2, template=nml_template, mode=mode)

    nml_1['someval']['val'] = 1
    nml_2['someval']['val'] = 1
