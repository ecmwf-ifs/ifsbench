# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
import os
from typing import Dict, List, Optional

import numpy as np
import xarray as xr

from ifsbench.data_file_reader import DataFileReader
from ifsbench.logging import error, warning


CFGRIB_AVAILABLE = False
ECCODES_AVAILABLE = False
PYGRIB_AVAILABLE = False

try:
    import eccodes
    from pkg_resources import packaging

    # pylint: disable=no-member
    if packaging.version.parse(eccodes.__version__) < packaging.version.parse('2.33.0'):
        raise ImportError('eccodes version too low.')
    # pylint: enable=no-member
    ECCODES_AVAILABLE = True
except (RuntimeError, ImportError):
    pass

if ECCODES_AVAILABLE:
    try:
        import cfgrib

        CFGRIB_AVAILABLE = True
    except (RuntimeError, ImportError):
        pass
    try:
        from pygrib import open as pgopen
        from pygrib import gribmessage

        PYGRIB_AVAILABLE = True
    except (RuntimeError, ImportError):
        pass

if not PYGRIB_AVAILABLE:
    # pylint: disable=function-redefined
    class gribmessage:
        pass

    # pylint: enable=function-redefined


__all__ = [
    'GribFileReader',
    'NoGribModification',
    'UniformGribNoiseFromMetadata',
    'modify_grib_file',
]


class GribFileReader(DataFileReader):

    @classmethod
    def read_data(cls, input_path: str) -> List[xr.Dataset]:
        """Reads GRIB file and returns data as dataframe.

        Note that cfgrib can be fickle and the GRIB data needs to be to spec.
            The data in the file is sorted into datasets based on levels and other parameters;
            this means that a single GRIB file can result in any number of dataframes.

        Args:
            input_path: Path to input GRIB file.

        Returns: List of datasets containing the data from the file.
        """
        if not CFGRIB_AVAILABLE:
            raise RuntimeError(f'Cannot read grib file {input_path}. cfgrib is not installed.')
        # pylint: disable=possibly-used-before-assignment
        return cfgrib.open_datasets(input_path, backend_kwargs={'indexpath': ''})


class GribModification(ABC):
    """Defines the noise to add to GribMessages"""

    def __init__(self):
        if not PYGRIB_AVAILABLE:
            raise RuntimeError(
                'Cannot modify GRIB files - pygrib or eccodes not available.'
            )

    @abstractmethod
    def modify_message(self, grb: gribmessage) -> gribmessage: # pylint: disable=possibly-used-before-assignment
        """Modifies the data in that GRIB message."""
        raise NotImplementedError()


class NoGribModification(GribModification):
    """Does not apply any modification."""

    def modify_message(self, grb: gribmessage) -> gribmessage:
        return grb


class UniformGribNoiseFromMetadata(GribModification):
    """Applies uniformly distributed noise to the data.

    The scale of the noise is given relative to a GRIB
    metadata field.
    """

    def __init__(self, noise_param: str, noise_scale: float):
        super().__init__()
        self._noise_param = noise_param
        self._noise_scale = noise_scale

    def modify_message(self, grb: gribmessage) -> gribmessage:
        if not grb.has_key('bitsPerValue') or grb['bitsPerValue'] == 0:
            # bitsPerValue == 0 indicates a constant value.
            warning(
                'Not modifying parameter %s: bitsPerValue is 0, constant value.',
                grb['shortName'],
            )
            return grb
        if not grb.has_key(self._noise_param) or grb[self._noise_param] == 0:
            error(
                'Cannot modify parameter %s: no value for %s which is used as a basis for the noise level.',
                grb['shortName'],
                self._noise_param,
            )
            raise ValueError('Missing noise parameter {self._noise_param}')
        grb.expand_grid(False)
        data_values = grb.values
        noise_max = grb[self._noise_param] * self._noise_scale
        data_mod = data_values + np.random.uniform(
            -noise_max, noise_max, data_values.shape
        )
        # TODO(ecm6397) Add checks for units `(Code table 4.xxx)` and `%`.
        if grb.has_key('units') and grb['units'] == '(0 - 1)':
            # Fractional parameters (e.g. cc) have to have values between 0 and 1.
            np.clip(data_mod, 0.0, 1.0, out=data_mod)
        grb.values = data_mod
        return grb


def _handle_grib_message(
    grb: gribmessage,
    base_modification: GribModification,
    parameter_config: Optional[Dict[str, GribModification]] = None,
) -> gribmessage:
    if parameter_config and grb['shortName'] in parameter_config:
        return parameter_config[grb['shortName']].modify_message(grb)

    return base_modification.modify_message(grb)


def modify_grib_file(
    input_path: str,
    output_path: str,
    base_modification: GribModification,
    parameter_config: Optional[Dict[str, GribModification]] = None,
    overwrite_existing: bool = False,
) -> None:
    """
    Modifies grib data and writes modified GRIB file.

    The noise scale specified in the config is a multiplier of the ``packingError`` field for that
    parameter.

    Parameters
    ----------
    input_path:
        Path to input GRIB file.
    output_path:
        This is where the modified data will be written.
    base_modification:
        Modification type to apply to all supported parameters
        unless otherwise specified in :data:`parameter_config`.
    parameter_config:
        shortNames of parameters that are to be modified and the class instance to apply.
    overwrite_existing:
        if output_path file exists, delete it. If False and file exists, exit.
    """
    if not PYGRIB_AVAILABLE:
        raise RuntimeError(
            'Cannot modify GRIB files - pygrib or eccodes not available.'
        )
    if not overwrite_existing and os.path.exists(output_path):
        error(
            'Output %s already exists and overwrite_existing is set to False.',
            output_path,
        )
        return
    with open(output_path, 'wb') as outfile:
        # pylint: disable=possibly-used-before-assignment
        grbs = pgopen(input_path)
        for grb in grbs:
            grb_mod = _handle_grib_message(grb, base_modification, parameter_config)
            msg = grb_mod.tostring()
            outfile.write(msg)

        grbs.close()
