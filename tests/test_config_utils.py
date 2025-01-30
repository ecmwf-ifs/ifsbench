import pathlib
import yaml

import pytest

from ifsbench import read_yaml_config
from ifsbench.data import (
    ExtractHandler,
    NamelistHandler,
    NamelistOperation,
    NamelistOverride,
)


def test_read_yaml_config(tmp_path: pathlib.Path):
    conf_path = str((tmp_path / 'test_conf.yaml').resolve())
    config = {
        'ext_handler': {
            'classname': 'ExtractHandler',
            'archive_path': 'big_tarball.tar.gz',
            'target_dir': 'input_data',
        },
        'nml_handler': {
            'classname': 'NamelistHandler',
            'input_path': 'namelist_in',
            'output_path': 'namelist_out',
            'overrides': [
                {
                    'namelist': 'NAMPAR0',
                    'entry': 'NPROC',
                    'mode': 'set',
                    'value': 16,
                },
                {
                    'namelist': 'NAMRIP',
                    'entry': 'CSTOP',
                    'mode': 'set',
                    'value': 'h24',
                },
                {
                    'namelist': 'NAMIO_SERV',
                    'entry': 'NPRNPROC_IOOC',
                    'mode': 'delete',
                },
            ],
        },
    }

    with open(conf_path, 'w', encoding="utf-8") as outf:
        yaml.dump(config, outf)

    run_conf = read_yaml_config(conf_path)

    assert 'ext_handler' in run_conf
    assert 'nml_handler' in run_conf

    # Check some sample objects for correctness.
    ext_handler = run_conf['ext_handler']
    assert isinstance(ext_handler, ExtractHandler)
    assert ext_handler.archive_path == 'big_tarball.tar.gz'

    nml_handler = run_conf['nml_handler']
    assert isinstance(nml_handler, NamelistHandler)
    assert len(nml_handler.overrides) == 3
    assert isinstance(nml_handler._overrides[0], NamelistOverride)
    no = nml_handler._overrides[0]
    assert no.mode == NamelistOperation.SET
    assert no.value == 16
    no = nml_handler._overrides[2]
    assert no.mode == NamelistOperation.DELETE
    assert no.value is None


def test_read_yaml_config_missing_class_fails(tmp_path: pathlib.Path):
    conf_path = str((tmp_path / 'test_conf.yaml').resolve())
    config = {
        'ext_handler': {
            'archive_path': 'big_tarball.tar.gz',
            'target_dir': 'input_data',
        },
    }

    with open(conf_path, 'w', encoding="utf-8") as outf:
        yaml.dump(config, outf)

    with pytest.raises(KeyError):
        read_yaml_config(conf_path)
