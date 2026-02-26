# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path

import pytest

from ifsbench import NetcdfFileReader


@pytest.fixture(name="netcdf_location")
def fixture_netcdf_location():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / "netcdf_files"


@pytest.fixture(name="grib_location")
def fixture_grib_location():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / "gribfiles"


def test_netcdffilereader_read_data(netcdf_location):
    input_path = netcdf_location / "o_fix.nc"

    fr = NetcdfFileReader()
    dss = fr.read_data(input_path=input_path)

    assert len(dss) == 1

    ds = dss[0]
    assert sorted(list(ds.coords)) == sorted(
        ["lat", "lon", "nlevs", "tile", "vtype", "nlevsn"]
    )
    assert sorted(list(ds.data_vars)) == sorted(["SoilThick", "SoilSat"])


def test_netcdffilereader_read_data_wrong_filetype_fails(grib_location):
    input_path = grib_location / "model_output_data_spectral.grb2"

    fr = NetcdfFileReader()
    with pytest.raises(OSError) as exceptinfo:
        fr.read_data(input_path=input_path)

    assert "NetCDF: Unknown file format" in str(exceptinfo.value)
