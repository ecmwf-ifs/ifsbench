# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for all classes that represent benchmark files
"""

from pathlib import Path
import tempfile

import pytest

from ifsbench import (
    InputFile, ExperimentFiles, SpecialRelativePath, DarshanReport,
    read_files_from_darshan, write_files_from_darshan
)


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve()


@pytest.fixture(name='experiment_files')
def fixture_experiment_files(here):
    """Return the full path to the directory with dummy experiment files"""
    return here/'experiment_files'


@pytest.fixture(name='experiment_files_dict')
def fixture_experiment_files_dict():
    return {
        'my-exp-id': {
            '/some/path/to/some/source/dir': {
                'sub/directory/inputA': {
                    'fullpath': '/some/path/to/some/source/dir/sub/directory/inputA',
                    'sha256sum': 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
                },
                'sub/directory/inputC': {
                    'fullpath': '/some/path/to/some/source/dir/sub/directory/inputC',
                    'sha256sum': 'bf07a7fbb825fc0aae7bf4a1177b2b31fcf8a3feeaf7092761e18c859ee52a9c'
                },
            },
            '/some/other/path/to/some/input/dir': {
                'subsub/dir/inputB': {
                    'fullpath': '/some/other/path/to/some/input/dir/subsub/dir/inputB',
                    'sha256sum': '7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730'
                },
            },
            '/the/path/to/ifsdata': {
                'some/inputD': {
                    'fullpath': '/the/path/to/ifsdata/some/inputD',
                    'sha256sum': 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'
                },
            },
        },
    }


def test_input_file(here):
    """
    Test representation of a single input file
    """
    # Test basic representation
    path = Path(__file__)
    input_file = InputFile(path, src_dir=here)
    assert str(input_file.path) == path.name
    assert input_file.fullpath == path
    assert input_file.src_dir == here

    # Test dumping and loading
    other_file = InputFile.from_dict(input_file.to_dict(), src_dir=here)
    assert str(other_file.path) == path.name
    assert other_file.fullpath == path
    assert other_file.src_dir == here

    # Test dumping and loading without src_dir
    extra_file = InputFile.from_dict(input_file.to_dict())
    assert extra_file.path == path.relative_to('/')
    assert extra_file.fullpath == path
    assert extra_file.src_dir == Path('/')

    # Test checksum verification
    extra_file.checksum = 'foobar'
    with pytest.raises(ValueError):
        InputFile.from_dict(extra_file.to_dict())

    # Test dumping and loading without checksum verification
    other_file._path = Path('foo.bar')  # pylint: disable=protected-access
    extra_file = InputFile.from_dict(other_file.to_dict(), verify_checksum=False)
    assert extra_file.path == (here/'foo.bar').relative_to('/')
    assert extra_file.fullpath == here/'foo.bar'
    assert extra_file.src_dir == Path('/')

    # Test equality of input files even with different paths
    the_file = InputFile(path, src_dir=here)
    also_the_file = InputFile(here/'..'/path.parent.name/path.name, src_dir=here.parent)
    assert the_file.fullpath != also_the_file.fullpath
    assert the_file.fullpath.resolve() == also_the_file.fullpath.resolve()
    assert the_file.checksum == also_the_file.checksum
    assert the_file == also_the_file

    with pytest.raises(OSError):
        _ = InputFile('/i_dont_exist', compute_metadata=True)


def test_experiment_files(tmp_path, experiment_files, experiment_files_dict):
    """
    Test discovery of files in src_dir
    """
    exp_setup = experiment_files_dict.copy()

    # Intentionally void the checksum for one file
    exp_setup['my-exp-id']['/the/path/to/ifsdata']['some/inputD']['sha256sum'] = \
        exp_setup['my-exp-id']['/the/path/to/ifsdata']['some/inputD']['sha256sum'][:-1]

    # Create ExperimentFiles object from the dict
    exp_files = ExperimentFiles.from_dict(exp_setup.copy(), verify_checksum=False)
    assert exp_files.exp_id == 'my-exp-id'
    assert len(exp_files.files) == 4
    assert len(exp_files.exp_files) == 3
    assert len(exp_files.ifsdata_files) == 1

    # Update the srcdir which automatically verifies the checksum
    with pytest.raises(ValueError):
        exp_files.update_srcdir(experiment_files, with_ifsdata=True)

    # Do the same but now with correct checksum
    exp_setup['my-exp-id']['/the/path/to/ifsdata']['some/inputD']['sha256sum'] += 'f'
    exp_files = ExperimentFiles.from_dict(exp_setup, verify_checksum=False)

    # Update the srcdir for exp_files but not ifsdata
    exp_files.update_srcdir(experiment_files)
    assert all(str(f.fullpath.parent) == str(experiment_files/'inidata') for f in exp_files.exp_files)
    assert all(str(f.fullpath.parent).startswith('/the/path/to') for f in exp_files.ifsdata_files)

    # Update srcdir for all
    exp_files.update_srcdir(experiment_files, with_ifsdata=True)
    assert all(str(f.fullpath.parent) == str(experiment_files/'inidata') for f in exp_files.exp_files)
    assert all(str(f.fullpath.parent) == str(experiment_files/'ifsdata') for f in exp_files.ifsdata_files)

    # Reload experiment from dict with checksum verification
    reloaded_exp_files = ExperimentFiles.from_dict(exp_files.to_dict(), verify_checksum=True)
    assert len(reloaded_exp_files.files) == 4
    assert len(reloaded_exp_files.exp_files) == 3
    assert len(reloaded_exp_files.ifsdata_files) == 1

    # Pack experiment files to tarballs
    exp_files.to_tarball(tmp_path, with_ifsdata=True)
    assert Path(tmp_path/experiment_files.name).with_suffix('.tar.gz').exists()
    assert Path(tmp_path/'ifsdata.tar.gz').exists()
    yaml_file = tmp_path/(exp_files.exp_id+'.yml')
    exp_files.to_yaml(yaml_file)

    # Unpack experiments
    reloaded_exp_files = ExperimentFiles.from_tarball(
        yaml_file, input_dir=tmp_path, output_dir=tmp_path, with_ifsdata=True)
    assert len(reloaded_exp_files.files) == 4
    assert len(reloaded_exp_files.exp_files) == 3
    assert len(reloaded_exp_files.ifsdata_files) == 1
    assert all(str(f.fullpath.parent).startswith(str(tmp_path))
                for f in reloaded_exp_files.files)


def test_experiment_files_from_darshan(here):
    """
    Test representation of darshan report in `ExperimentFiles`
    """
    report = DarshanReport(here/'darshan.log')
    read_files = read_files_from_darshan(report)
    write_files = write_files_from_darshan(report)
    input_files = read_files - write_files

    # Test basic representation
    exp_files = ExperimentFiles('abcd')
    exp_files.add_file(*input_files, compute_metadata=False)
    assert len(exp_files.files) == 27
    assert len(exp_files.exp_files) == 15
    assert len(exp_files.ifsdata_files) == 12

    # Test dumping and loading
    other_files = ExperimentFiles.from_dict(exp_files.to_dict(), verify_checksum=False)
    assert {str(f.fullpath) for f in exp_files.files}=={str(f.fullpath) for f in other_files.files}

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        yaml_file = Path(tmp_dir)/'experiment_files.yml'
        exp_files.to_yaml(yaml_file)
        other_files = ExperimentFiles.from_yaml(yaml_file, verify_checksum=False)


def test_special_relative_path():
    """
    Test correct mapping of paths with :any:`SpecialRelativePath`
    """
    mapper = SpecialRelativePath(r"^(?:.*?\/)?(?P<name>[^\/]+)$", r"relative/to/\g<name>")

    assert mapper('/this/is/some/path') == 'relative/to/path'
    assert mapper('relative/path') == 'relative/to/path'
    assert mapper('path') == 'relative/to/path'
    assert mapper('/invalid/path/') == '/invalid/path/'

    mapper = SpecialRelativePath.from_filename(
        'wam_', r'\g<post>', match=SpecialRelativePath.NameMatch.LEFT_ALIGNED)

    assert mapper('/this/is/some/path') == '/this/is/some/path'
    assert mapper('/path/to/wam_sfcwindin') == 'sfcwindin'
    assert mapper('relative/path/to/wam_cdwavein') == 'cdwavein'
    assert mapper('wam_specwavein') == 'specwavein'
    assert mapper('/some/wam_specwavein/file') == '/some/wam_specwavein/file'

    mapper = SpecialRelativePath.from_filename(
        r'rtablel_\d+', r'ifs/\g<name>', match=SpecialRelativePath.NameMatch.EXACT)

    assert mapper('/absolute/path/to/rtablel_2063') == 'ifs/rtablel_2063'
    assert mapper('relative/to/rtablel_2063') == 'ifs/rtablel_2063'
    assert mapper('rtablel_2063') == 'ifs/rtablel_2063'
    assert mapper('/some/rtablel_a2063') == '/some/rtablel_a2063'
    assert mapper('rtablel_2063/abc') == 'rtablel_2063/abc'
    assert mapper('tl159/hjpa/install_SP/share/odb/rtablel_2063') == 'ifs/rtablel_2063'

    mapper = SpecialRelativePath.from_dirname(
        'ifsdata', r'ifsdata\g<child>', match=SpecialRelativePath.NameMatch.EXACT)

    assert mapper('data/ifsdata/greenhouse_gas_climatology_46r1.nc') == \
        'ifsdata/greenhouse_gas_climatology_46r1.nc'
    assert mapper('/perm/rd/nabr/ifsbench-setups/v2/data/ifsdata/RADRRTM') == 'ifsdata/RADRRTM'
