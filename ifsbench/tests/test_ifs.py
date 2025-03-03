# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Test :any:`IFS` and adjacent classes
"""
from pathlib import Path
import pytest
from ifsbench import ifs


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve()


@pytest.fixture(name='namelists')
def fixture_namelists(here):
    """Return the full path of the namelists directory"""
    return here/'namelists'


@pytest.mark.parametrize('cycle,expected_type', [
    ('CY46R1', ifs.IFS_CY46R1),
    ('cy46r1', ifs.IFS_CY46R1),
    ('CY47R1', ifs.IFS_CY47R1),
    ('cy47r1', ifs.IFS_CY47R1),
    ('CY47R2', ifs.IFS_CY47R2),
    ('cy47r2', ifs.IFS_CY47R2),
    (None, ifs.IFS_CY47R2),
    ('default', ifs.IFS_CY47R2),
])
def test_ifs_construction(cycle, expected_type):
    """
    Test correct setup of IFS cycles
    """
    obj = ifs.IFS.create_cycle(cycle, builddir='.')
    assert isinstance(obj, expected_type)


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
@pytest.mark.parametrize('prec', ('sp', 'dp'))
def test_ifs(cycle, prec):
    """
    Verify that some of the default properties return sensible values
    """
    if cycle == 'cy46r1':
        # No Single Precision support
        exec_name = 'ifsMASTER.DP'
        ld_library_path = 'build/ifs-source'
        obj_default = ifs.IFS.create_cycle(cycle, builddir='build')
        obj_install = ifs.IFS.create_cycle(cycle, builddir='build', installdir='../prefix')
    else:
        exec_name = f'ifsMASTER.{prec.upper()}'
        ld_library_path = f'build/ifs_{prec}'
        obj_default = ifs.IFS.create_cycle(cycle, builddir='build', prec=prec)
        obj_install = ifs.IFS.create_cycle(cycle, builddir='build', installdir='../prefix', prec=prec)

    assert obj_default.exec_name == exec_name
    assert str(obj_default.executable) == 'build/bin/' + exec_name
    assert any(ld_library_path in path for path in obj_default.ld_library_paths)

    assert obj_default.exec_name == exec_name
    assert str(obj_install.executable) == '../prefix/bin/' + exec_name
    assert any(ld_library_path in path for path in obj_install.ld_library_paths)


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
@pytest.mark.parametrize('prec', ('sp', 'dp'))
def test_ifs_setup_env(cycle, prec):
    """
    Verify that a given number of default parameters is present in the env
    """
    default_keys = {'DATA', 'GRIB_DEFINITION_PATH', 'GRIB_SAMPLES_PATH', 'NPROC', 'NPROC_IO'}

    if cycle == 'cy46r1':
        # No Single Precision support
        obj = ifs.IFS.create_cycle(cycle, builddir='build')
    else:
        obj = ifs.IFS.create_cycle(cycle, builddir='build', prec=prec)
    env, kwargs = obj.setup_env(rundir='.', nproc=1337, nproc_io=42, namelist=None, nthread=1,
                                hyperthread=1, arch=None)
    assert kwargs == {}
    assert default_keys <= set(env.keys())

    env, kwargs = obj.setup_env(rundir='../..', env={'abc': 123, 'foo': 666}, nproc=1, nproc_io=0,
                                namelist=None, nthread=1, hyperthread=1, arch=None, foobar='baz')
    assert kwargs == {'foobar': 'baz'}
    assert (default_keys | {'abc', 'foo'}) <= set(env.keys())

    # make sure path for libblack.so is set
    if cycle == 'cy46r1':
        assert 'LD_LIBRARY_PATH' in env and 'build/ifs-source:' in env['LD_LIBRARY_PATH']
    else:
        assert 'LD_LIBRARY_PATH' in env and f'build/ifs_{prec}:' in env['LD_LIBRARY_PATH']


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
def test_ifs_setup_nml(namelists, cycle):
    """
    Verify that a given number of default parameters is set correctly
    in the namelist
    """
    default_params = (
        (('nampar0', 'nproc'), 7),
        (('namio_serv', 'nproc_io'), 5),
    )

    obj = ifs.IFS.create_cycle(cycle, builddir='build')
    nml, kwargs = obj.setup_nml(namelist=(namelists/'t21_fc.nml'), rundir='.', nproc=12, nproc_io=5,
                                nthread=1, hyperthread=1, arch=None, foobar='baz')
    assert kwargs == {'foobar': 'baz'}
    groups = tuple(nml.nml.groups())
    assert all(param in groups for param in default_params)

    nml, kwargs = obj.setup_nml(namelist=(namelists/'t21_fc.nml'), rundir='.', nproc=12, nproc_io=5,
                                fclen='d10', nthread=1, hyperthread=1, arch=None)
    assert kwargs == {}
    groups = tuple(nml.nml.groups())
    default_params += ((('namrip', 'cstop'), 'd10'),)
    assert all(param in groups for param in default_params)


@pytest.mark.parametrize('cycle', [None, 'cy1', 'foobar', 'cy100'])
def test_ifs_setup_invalid(cycle):
    """Verify that an invalid cycle key will use the default value"""

    assert cycle not in ifs.cycle_registry
    obj = ifs.IFS.create_cycle(cycle, builddir='builddir')
    assert isinstance(obj, ifs.cycle_registry['default'])
