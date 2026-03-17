# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for the PerturbationHandler class.
"""

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from ifsbench.data import GaussianNoise, PerturbationHandler, UniformNoise


@pytest.fixture(name='datafiles')
def fixture_datafiles():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / 'datafiles'


def test_uniform_noise():

    uniform = UniformNoise(min_value=10.0, max_value=10.1)
    rng = np.random.default_rng()

    result = uniform.generate(rng, 5)

    assert len(result) == 5

    assert all(i >= 10.0 for i in result)
    assert all(i < 10.1 for i in result)


def test_gaussian_noise():

    gauss = GaussianNoise(mean=20, width=2)
    rng = np.random.default_rng()

    # Large number so we can actually check the distribution.
    result = gauss.generate(rng, 1000)

    assert len(result) == 1000
    assert abs(np.mean(result) - 20) < 0.3
    assert abs(np.median(result) - 20) < 0.3
    assert abs(np.std(result) - 2) < 0.3


def test_perturbationhandler_config():
    config = {
        'data_file': 'somewhere',
        'perturbations': {
            'var1': {'class_name': 'UniformNoise', 'min_value': 1, 'max_value': 2},
            'var2': {'class_name': 'GaussianNoise', 'mean': 1, 'width': 0.5},
        },
        'output_file': 'elsewhere',
    }

    handler = PerturbationHandler.from_config(config)

    assert len(handler.perturbations) == 2
    assert list(handler.perturbations.keys()) == ['var1', 'var2']
    assert isinstance(handler.perturbations['var1'], UniformNoise)
    assert isinstance(handler.perturbations['var2'], GaussianNoise)
    assert handler.random_seed is None

    assert handler.dump_config() == config


def test_perturbationhandler_config_seed():
    config = {
        'data_file': 'somewhere',
        'perturbations': {'class_name': 'UniformNoise', 'min_value': 1, 'max_value': 2},
        'output_file': 'elsewhere',
        'random_seed': 42,
    }

    handler = PerturbationHandler.from_config(config)

    assert isinstance(handler.perturbations, UniformNoise)
    assert handler.random_seed == 42

    assert handler.dump_config() == config


def test_perturbationhandler_execute_single_noise(tmp_path, datafiles):
    input_path = datafiles / 'surfclim_partial.nc'
    output_file = 'modified.nc'
    noise = UniformNoise(min_value=1, max_value=2)

    handler = PerturbationHandler(
        data_file=input_path, perturbations=noise, output_file=output_file
    )

    handler.execute(tmp_path)

    output_path = tmp_path / output_file
    assert output_path.exists()

    original = xr.open_dataset(input_path, engine='netcdf4', decode_times=False)
    modified = xr.open_dataset(output_path, engine='netcdf4', decode_times=False)
    difference = modified - original

    for var in original.data_vars:
        assert difference[var].min() >= 1
        assert difference[var].max() <= 2


def test_perturbationhandler_execute_seed_reproducible(tmp_path, datafiles):
    input_path = datafiles / 'surfclim_partial.nc'
    noise = UniformNoise(min_value=1, max_value=2)

    output_file_1 = 'modified_1.nc'
    PerturbationHandler(
        data_file=input_path, perturbations=noise, output_file=output_file_1, random_seed=42
    ).execute(tmp_path)

    output_file_2 = 'modified_2.nc'
    PerturbationHandler(
        data_file=input_path, perturbations=noise, output_file=output_file_2, random_seed=42
    ).execute(tmp_path)

    output_path_1 = tmp_path / output_file_1
    output_path_2 = tmp_path / output_file_2

    modified_1 = xr.open_dataset(output_path_1, engine='netcdf4', decode_times=False)
    modified_2 = xr.open_dataset(output_path_2, engine='netcdf4', decode_times=False)

    assert modified_1 == modified_2


def test_perturbationhandler_execute_noise_pert(tmp_path, datafiles):
    input_path = datafiles / 'surfclim_partial.nc'
    output_file = 'modified.nc'
    noise = {'cvh': UniformNoise(min_value=1, max_value=2), 'tvh': GaussianNoise(mean=100, width=1)}

    handler = PerturbationHandler(
        data_file=input_path, perturbations=noise, output_file=output_file
    )

    handler.execute(tmp_path)

    output_path = tmp_path / output_file
    assert output_path.exists()

    original = xr.open_dataset(input_path, engine='netcdf4', decode_times=False)
    modified = xr.open_dataset(output_path, engine='netcdf4', decode_times=False)
    difference = modified - original

    for var in original.data_vars:
        if var not in noise:
            np.testing.assert_array_equal(modified[var], original[var])

    assert difference['cvh'].min() >= 1
    assert difference['cvh'].max() <= 2

    assert abs(difference['tvh'].mean() - 100) < 1
    assert abs(difference['tvh'].std() - 1) < 0.5
