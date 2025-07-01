# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pathlib
from typing import Dict, List, Union

import yaml

from ifsbench.config_mixin import DataClass
from ifsbench.data import ExtractHandler, NamelistHandler
from ifsbench.results import EnsembleStats

__all__ = ['read_yaml_config']

_SUPPORTED_CONFIGS = {
    'ExtractHandler': ExtractHandler,
    'NamelistHandler': NamelistHandler,
    'EnsembleStats': EnsembleStats,
}


def _parse_config(
    config: Dict[str, Union[str, float, int, bool, List, None]]
) -> Dict[str, DataClass]:
    result = {}
    # for key, value in config.items():
    #     classname = value.pop(CLASSNAME, '')
    #     clazz = _SUPPORTED_CONFIGS[classname]
    #     result[key] = clazz.from_config(value)
    return result


def read_yaml_config(input_path: str) -> Dict[str, DataClass]:
    """Read config from file in yam format.

    Args:
        input_path: path to yaml file.

    Returns:
        Dictionary of ConfigMixin-type objects by their name as specified in
          the input configuration.
    """
    input_file = pathlib.Path(input_path)
    with open(input_file, encoding="utf-8") as infile:
        config = yaml.safe_load(infile)
    return _parse_config(config)
