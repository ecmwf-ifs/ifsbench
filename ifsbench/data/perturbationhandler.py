# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import abstractmethod
import pathlib
from typing import Dict, Optional, Tuple, Union

import numpy as np
import xarray as xr

from ifsbench.data.datahandler import absolutise_path, DataHandler
from ifsbench.serialisation_mixin import SubclassableSerialisationMixin

__all__ = ['PerturbationHandler', 'RandomNoise', 'UniformNoise', 'GaussianNoise']


class RandomNoise(SubclassableSerialisationMixin):
    """
    Abstract class for generating arrays of random numbers.
    """

    @abstractmethod
    def generate(self, rng: np.random.Generator, size: Union[int, Tuple[int]]) -> np.ndarray:
        """
        Generate array of specified size of random numbers using the provided Generator.
        """
        return NotImplemented


class UniformNoise(RandomNoise):
    """
    Generate uniform noise in the given interval [min_value, max_value)

    Parameters:
        min_value: The lower bound of the interval.
        max_value: The upper bound of the interval.
    """

    min_value: float
    max_value: float

    def generate(self, rng: np.random.Generator, size: Union[int, Tuple[int]]) -> np.ndarray:
        return rng.uniform(low=self.min_value, high=self.max_value, size=size)


class GaussianNoise(RandomNoise):
    """
    Generate random noise from a normal distribution.

    Parameters:
        mean: The centre of the distribution.
        width: The width (sigma) of the distribution.
    """

    mean: float
    width: float

    def generate(self, rng: np.random.Generator, size: Union[int, Tuple[int]]) -> np.ndarray:
        return rng.normal(loc=self.mean, scale=self.width, size=size)


class PerturbationHandler(DataHandler):
    """
    DataHandler to add random noise to data. Uses a netCDF file as input and writes output to a new netCDF file.

    Parameters
    ----------
    data_file: :any:`pathlib.Path`
        NetCDF file containing the data to be modified.
    perturbations: RandomNoise or dict[str, RandomNoise]
        Either a RandomNoise implementation which will be applied to all data variables in the input file,
        or a dictionary of {variable: RandomNoise} where the RandomNoise instance will be applied to that variable.
        Variables not in the dictionary will not be modified.
    output_file: :any:`pathlib.Path`
        Path to output file.
    random_seed: int or None
        Optional random seed to use for Generator.
        If None, system default will be used which changes every time.
    """

    data_file: pathlib.Path
    perturbations: Union[Dict[str, RandomNoise], RandomNoise]
    output_file: pathlib.Path
    random_seed: Optional[int] = None

    def execute(self, wdir: Union[str, pathlib.Path], **kwargs) -> None:
        input_path = absolutise_path(wdir, self.data_file)
        target_path = absolutise_path(wdir, self.output_file)

        rng = np.random.default_rng(self.random_seed)

        # decode_times = False due to issues with encoding of 'month' in cftime.
        # Times are not needed here, so leave them as is.
        data = xr.open_dataset(input_path, engine='netcdf4', decode_times=False)

        pert_data = data.copy()

        if isinstance(self.perturbations, RandomNoise):
            pert_dict = {data_var: self.perturbations for data_var in list(pert_data.data_vars)}
        else:
            pert_dict = self.perturbations

        for var, pert in pert_dict.items():
            noise = pert.generate(rng, pert_data[var].shape)
            pert_data[var] += noise

        pert_data.to_netcdf(target_path)
