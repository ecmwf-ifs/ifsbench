# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from pathlib import Path
import pytest

import numpy as np
import xarray as xr

from ifsbench import gribfile
from ifsbench import (
    GribFileReader,
    NoGribModification,
    UniformGribNoiseFromMetadata,
    modify_grib_file,
)


@pytest.fixture(name="here")
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / "gribfiles"


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason="could not import cfgrib, likely missing eccodes.",
)
def test_gribfilereader_read_data(here):
    input_path = here / "model_output_data_pl.grb2"

    gf = GribFileReader()
    dss = gf.read_data(input_path)

    assert len(dss) == 1

    ds = dss[0]
    assert sorted(list(ds.coords)) == sorted(
        ["isobaricInhPa", "latitude", "longitude", "step", "time", "valid_time"]
    )


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason="could not import cfgrib, likely missing eccodes.",
)
def test_gribfilereader_read_data_multiple_datasets(here):
    input_path = here / "model_output_data_rad.grb2"

    gf = GribFileReader()
    dss = gf.read_data(input_path)

    assert len(dss) == 2

    ds = dss[0]
    assert sorted(list(ds.coords)) == sorted(
        ["latitude", "longitude", "step", "time", "valid_time", "nominalTop"]
    )


def _read_grib(input_path: str, short_name: str) -> xr.Dataset:
    ds = xr.open_dataset(
        input_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {"shortName": short_name},
            "indexpath": "",
            "read_keys": ["packingError"],
        },
    )
    return ds


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason="could not import pygrib or cfgrib, likely missing eccodes.",
)
def test_modify_grib_file(here, tmp_path):
    noise_scale = 1.0001
    input_path = here / "model_input_data_stl.grb"
    output_path = tmp_path / "out.grib"
    params = ["stl1", "stl2"]

    no_noise = NoGribModification()
    uniform_noise = UniformGribNoiseFromMetadata(
        noise_param="packingError", noise_scale=noise_scale
    )
    noise_config = dict.fromkeys(params, uniform_noise)

    modify_grib_file(
        str(input_path),
        output_path,
        base_modification=no_noise,
        parameter_config=noise_config,
    )

    # confirm that stl2 has been modified
    param = params[1]
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])
    packing_error = ds_ref[param].attrs["GRIB_packingError"]

    assert abs(comp_max) > 0
    assert abs(comp_min) > 0
    assert abs(comp_max) <= 2 * packing_error * noise_scale
    assert abs(comp_min) <= 2 * packing_error * noise_scale

    # confirm that stl3 has not been modified
    param = "stl3"
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])

    assert comp_max == 0
    assert comp_min == 0


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason="could not import pygrib or cfgrib, likely missing eccodes.",
)
def test_modify_grib_fractionparam(here, tmp_path):
    noise_scale = 1.001
    input_path = here / "model_input_data_fractionparam.grb"
    output_path = tmp_path / "out.grib"
    params = ["cc", "crwc"]

    uniform_noise = UniformGribNoiseFromMetadata(
        noise_param="packingError", noise_scale=noise_scale
    )

    modify_grib_file(str(input_path), output_path, base_modification=uniform_noise)

    # confirm that cc has been modified and clipped to [0,1]
    param = params[0]
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])
    packing_error = ds_ref[param].attrs["GRIB_packingError"]

    assert abs(comp_max) > 0
    assert abs(comp_min) > 0
    assert abs(comp_max) <= 2 * packing_error * noise_scale
    assert abs(comp_min) <= 2 * packing_error * noise_scale

    assert np.nanmin(ds_mod[param]) >= 0
    assert np.nanmax(ds_mod[param]) <= 1

    # confirm that crwc (constant value) has not been modified
    param = params[1]
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])

    assert comp_max == 0
    assert comp_min == 0


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason="could not import pygrib or cfgrib, likely missing eccodes.",
)
def test_modify_grib_output_exists(here, tmp_path):
    input_path = here / "model_input_data_stl.grb"
    output_path = tmp_path / "out.grib"

    no_noise = NoGribModification()

    # Create the output and set its mtime and atime to the past.
    with output_path.open(mode="w"):
        pass
    os.utime(output_path, ns=(1000, 1000))

    modify_grib_file(str(input_path), output_path, no_noise)

    # Confirm that file times have not changed and the file is empty,
    # i.e. nothing was written.
    statinfo = os.stat(output_path)
    assert statinfo.st_mtime_ns == 1000
    assert statinfo.st_size == 0


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason="could not import pygrib or cfgrib, likely missing eccodes.",
)
def test_modify_grib_output_exists_allow_overwrite(here, tmp_path):
    input_path = here / "model_input_data_stl.grb"
    output_path = tmp_path / "out.grib"

    no_noise = NoGribModification()

    # Create the output and set its mtime and atime to the past.
    with output_path.open(mode="w"):
        pass
    os.utime(output_path, ns=(1000, 1000))

    modify_grib_file(str(input_path), output_path, no_noise, overwrite_existing=True)

    # Confirm that file times have not changed and the file is empty,
    # i.e. nothing was written.
    statinfo = os.stat(output_path)
    assert statinfo.st_mtime_ns > 1000
    assert statinfo.st_size > 0
