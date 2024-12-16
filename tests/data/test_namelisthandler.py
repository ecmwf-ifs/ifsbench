# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for all classes that represent benchmark files
"""

from contextlib import nullcontext
from pathlib import Path

from f90nml import Namelist
import pytest

from ifsbench.data import (
    NamelistHandler, NamelistOverride
)

@pytest.fixture(name = 'initial_namelist')
def fixture_namelist():
    namelist = Namelist()

    namelist['namelist1'] = {
        'int': 2,
        'str': 'test',
        'list': [2, 3, 'entry']
    }

    namelist['namelist2'] = {'int': 5}

    return namelist


@pytest.mark.parametrize('key,mode,value,success', [
    ('namelist1', NamelistOverride.NamelistOperation.APPEND, None, False),
    ('namelist1', NamelistOverride.NamelistOperation.SET, None, False),
    ('namelist1', NamelistOverride.NamelistOperation.DELETE, None, False),
    ('namelist1/entry', NamelistOverride.NamelistOperation.DELETE, None, True),
    ('namelist1/entry', NamelistOverride.NamelistOperation.SET, None, False),
    ('namelist1/entry', NamelistOverride.NamelistOperation.APPEND, None, False),
    ('namelist1/entry', NamelistOverride.NamelistOperation.SET, 2, True),
    ('namelist1/entry', NamelistOverride.NamelistOperation.APPEND, 3, True),
    (('namelist1', 'entry'), NamelistOverride.NamelistOperation.SET, 2, True),
    (('namelist1', 'entry'), NamelistOverride.NamelistOperation.APPEND, 3, True),
])
def test_extracthandler_init(key, mode, value, success):
    """
    Initialise the NamelistOverride and make sure that only correct values are
    accepted.
    """

    if success:
        context = nullcontext()
    else:
        context = pytest.raises(ValueError)

    with context:
        NamelistOverride(key, mode, value)


@pytest.mark.parametrize('key,value', [
    (('namelist1', 'int'), 5),
    (('namelist1', 'list'), [0, 2]),
    (('namelist2', 'int'), 'not an int'),
    (('namelist2', 'newvalue'), 5),
    (('namelist3', 'anothervalue'), [2,3,4]),
])
def test_extracthandler_apply_set(initial_namelist, key, value):
    """
    Initialise the NamelistOverride and make sure that only correct values are accepted.
    """

    namelist = Namelist(initial_namelist)

    override = NamelistOverride(key, NamelistOverride.NamelistOperation.SET, value)

    override.apply(namelist)

    assert namelist[key[0]][key[1]] == value

    for name, entry in namelist.items():
        for name2 in entry.keys():
            if (name, name2) != key:
                assert entry[name2] == initial_namelist[name][name2]

@pytest.mark.parametrize('key,value,success', [
    (('namelist1', 'int'), 5, False),
    (('namelist1', 'list'), 3, True),
    (('namelist1', 'list'), [2, 4], False),
    (('namelist1', 'list'), 5, True),
    (('namelist1', 'list'), 'Hello', False),
    (('namelist2', 'int'), 'not an int', False),
    (('namelist3', 'new_list'), 'not an int', True)
])
def test_extracthandler_apply_append(initial_namelist, key, value, success):
    """
    Initialise the NamelistOverride and make sure that only correct values are accepted.
    """

    namelist = Namelist(initial_namelist)

    override = NamelistOverride(key, NamelistOverride.NamelistOperation.APPEND, value)

    if success:
        override.apply(namelist)
    else:
        with pytest.raises(ValueError):
            override.apply(namelist)
        return

    if key[0] in initial_namelist and key[1] in initial_namelist[key[0]]:
        assert namelist[key[0]][key[1]] == initial_namelist[key[0]][key[1]] + [value]
    else:
        assert namelist[key[0]][key[1]] == [value]


    for name, entry in namelist.items():
        for name2 in entry.keys():
            if (name, name2) != key:
                assert entry[name2] == initial_namelist[name][name2]


@pytest.mark.parametrize('key', [
    ('namelist1', 'int'),
    ('namelist1', 'list'),
    ('namelist1', 'list'),
    ('namelist2', 'int'),
    ('doesnot', 'exist'),
    ('namelist1', 'missing'),
])
def test_extracthandler_apply_delete(initial_namelist, key):
    """
    Initialise the NamelistOverride and make sure that only correct values are accepted.
    """

    namelist = Namelist(initial_namelist)

    override = NamelistOverride(key, NamelistOverride.NamelistOperation.DELETE)

    override.apply(namelist)

    for name, entry in initial_namelist.items():
        for name2 in entry.keys():
            if (name, name2) == key:
                if name in namelist:
                    assert name2 not in namelist[name]
            else:
                assert namelist[name][name2] == initial_namelist[name][name2]


@pytest.mark.parametrize('input_path,input_valid', [
    (Path('somewhere/fort.4'), True),
    ('somewhere/namelist', True),
    (None, False),
    (2, False)
])
@pytest.mark.parametrize('output_path,output_valid', [
    (Path('somewhere/new_fort.4'), True),
    ('somewhere/namelist', True),
    (None, False),
    (2, False)
])
@pytest.mark.parametrize('overrides, overrides_valid', [
    ([], True),
    ('Test', False),
    (2, False),
    ([NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.SET, 5)], True),
    ([
        NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.SET, 5),
        NamelistOverride('namelist/entry2', NamelistOverride.NamelistOperation.APPEND, 2),
        NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.DELETE),

    ], True),
])
def test_namelisthandler_init(input_path, input_valid, output_path, output_valid, overrides, overrides_valid):
    """
    Initialise the NamelistHandler and make sure that only correct values are accepted.
    """
    if input_valid and output_valid and overrides_valid:
        context = nullcontext()
    else:
        context = pytest.raises(Exception)

    with context:
        NamelistHandler(input_path, output_path, overrides)



@pytest.mark.parametrize('input_path', [
    Path('somewhere/fort.4'),
    'somewhere/namelist'
])
@pytest.mark.parametrize('input_relative', [True, False])
@pytest.mark.parametrize('output_path', [
    Path('somewhere_else/new_fort.4'),
    'somewhere/namelist',
])
@pytest.mark.parametrize('output_relative', [True, False])
@pytest.mark.parametrize('overrides', [
    [],
    [NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.SET, 5)],
    [
        NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.SET, 5),
        NamelistOverride('namelist/entry2', NamelistOverride.NamelistOperation.APPEND, 2),
        NamelistOverride('namelist/entry', NamelistOverride.NamelistOperation.DELETE),

    ],
])

def test_namelisthandler_execute(tmp_path, initial_namelist, input_path,
                                 input_relative, output_path, output_relative,
                                 overrides):
    """
    Test that the execute function modifies the namelists correctly.

        Parameters
        ----------
        tmp_path: `pathlib.Path`
            pytest-provided temporary directory which acts as our working directory.

        input_path:
            Relative path (to tmp_path) where the input namelist resides.

        input_relative:
            Whether input_path will be passed to the NamelistHandler as a relative
            or absolute path.

        output_path:
            Relative path (to tmp_path) to the output namelist.

        output_relative:
            Whether output_path will be passed to the NamelistHandler as a relative
            or absolute path.

        overrides:
            The overrides that are applied.

    """
    # Build the paths that are passed to the NamelistHandler. If the paths
    # are supposed to be absolute, use tmp_path to build an absolute path.
    # Also distinguish between str and Path (ExtractHandler should support
    # both).
    if not input_relative:
        if isinstance(input_path, str):
            input_path = str((tmp_path/input_path).resolve())
        else:
            input_path = (tmp_path/input_path).resolve()

    if not output_relative:
        if isinstance(output_path, str):
            output_path = str((tmp_path/output_path).resolve())
        else:
            output_path = (tmp_path/output_path).resolve()

    # Create the initial namelist.

    abs_input_path = tmp_path/output_path

    abs_input_path.parent.mkdir(parents=True, exist_ok=True)
    initial_namelist.write(abs_input_path)


    # Actually extract the archive.
    handler = NamelistHandler(input_path, output_path, overrides)
    handler.execute(tmp_path)

    if output_relative:
        assert (tmp_path/output_path).exists()
    else:
        assert Path(output_path).exists()
