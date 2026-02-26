# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
import pytest

from ifsbench import gribfile, data_file_stats
from ifsbench import (
    DataFileStats,
    DataFileType,
)


@pytest.fixture(name="grib_location")
def fixture_grib_location():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / "gribfiles"


@pytest.fixture(name="netcdf_location")
def fixture_netcdf_location():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / "netcdf_files"


def test_from_config_full():
    config_in = {
        "input_path": "some/where",
        "stat_names": ["s1", "s2"],
        "stat_dims": ["d1", "d2"],
        "filetype": DataFileType.GRIB,
    }

    dfs = DataFileStats.from_config(config_in)

    # input_path cast to Path
    assert dfs.input_path == Path("some/where")
    assert dfs.stat_names == ["s1", "s2"]
    # dims cast to set
    assert dfs.stat_dims == {"d1", "d2"}
    assert dfs.filetype == "grib"


def test_from_config_minimal():
    config_in = {"input_path": "some/where"}

    dfs = DataFileStats.from_config(config_in)

    # input_path cast to Path
    assert dfs.input_path == Path("some/where")
    assert dfs.stat_names == data_file_stats._DEFAULT_STAT_NAMES
    assert dfs.stat_dims == data_file_stats._DEFAULT_STAT_DIMS
    assert dfs.filetype is None


def test_dump_config_full():
    config_in = {
        "input_path": "some/where",
        "stat_names": ["s1", "s2"],
        "stat_dims": ["d1", "d2"],
        "filetype": DataFileType.GRIB,
    }

    dfs = DataFileStats.from_config(config_in)
    config_out = dfs.dump_config()

    assert len(config_out) == 4
    assert config_out["input_path"] == "some/where"
    assert config_out["stat_names"] == ["s1", "s2"]
    assert set(config_out["stat_dims"]) == {"d1", "d2"}
    assert config_out["filetype"] == "grib"


def test_dump_config_minimal():
    config_in = {"input_path": "some/where"}

    dfs = DataFileStats.from_config(config_in)
    config_out = dfs.dump_config()

    assert len(config_out) == 3
    assert config_out["input_path"] == "some/where"
    assert config_out["stat_names"] == data_file_stats._DEFAULT_STAT_NAMES
    assert set(config_out["stat_dims"]) == set(data_file_stats._DEFAULT_STAT_DIMS)
    assert "filetype" not in config_out


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason="could not import cfgrib, likely missing eccodes.",
)
def test_get_stats_grib_pressurelevels_single_dataset(grib_location):
    input_path = grib_location / "model_output_data_pl.grb2"

    gf = DataFileStats(input_path=input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 1

    df = dfs[0]
    # shape ((2step x 2 level x 7 stats), (time, valid_time, u, v))
    assert df.shape == (28, 4)
    assert sorted(list(df.columns)) == sorted(["time", "valid_time", "u", "v"])

    # Sanity check relative values
    ds = df.to_xarray()
    for data_var in ["u", "v"]:
        for s in ds.step:
            for p in ds.isobaricInhPa:
                print(f"{data_var} - {s} - {p}")
                d = ds[data_var].sel(step=s, isobaricInhPa=p)
                assert (
                    d.sel(stat="min")
                    < d.sel(stat="p5")
                    < d.sel(stat="p10")
                    < d.sel(stat="mean")
                    < d.sel(stat="p90")
                    < d.sel(stat="p95")
                    < d.sel(stat="max")
                )


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason="could not import cfgrib, likely missing eccodes.",
)
def test_get_stats_grib_two_datasets(grib_location):
    input_path = grib_location / "model_output_data_rad.grb2"

    gf = DataFileStats(input_path=input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 2

    df = dfs[0]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ttr))
    assert df.shape == (14, 4)
    assert sorted(list(df.columns)) == sorted(
        ["time", "valid_time", "ttr", "nominalTop"]
    )

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
        d = ds["ttr"].sel(step=s)
        assert (
            d.sel(stat="min")
            < d.sel(stat="p5")
            < d.sel(stat="p10")
            < d.sel(stat="mean")
            < d.sel(stat="p90")
            < d.sel(stat="p95")
            < d.sel(stat="max")
        )

    df = dfs[1]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ssr))
    assert df.shape == (14, 4)
    assert sorted(list(df.columns)) == sorted(["time", "valid_time", "ssr", "surface"])

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
        d = ds["ssr"].sel(step=s)
        assert (
            d.sel(stat="min")
            <= d.sel(stat="p5")
            <= d.sel(stat="p10")
            < d.sel(stat="mean")
            < d.sel(stat="p90")
            < d.sel(stat="p95")
            <= d.sel(stat="max")
        )


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason="could not import cfgrib, likely missing eccodes.",
)
def test_get_stats_grib_spectral(grib_location):
    input_path = grib_location / "model_output_data_spectral.grb2"

    gf = DataFileStats(input_path=input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 4

    df = dfs[0]
    # shape ((19 levels x 7 stats), (time, valid_time, step, t))
    assert df.shape == (133, 4)
    assert sorted(list(df.columns)) == sorted(["time", "valid_time", "t", "step"])

    # Sanity check relative values
    ds = df.to_xarray()
    for level in ds.hybrid:
        d = ds["t"].sel(hybrid=level)
        print(f"level: {level}, data:\n{d}")
        # In this case, p90 < mean, therefore splitting the checks.
        assert (
            d.sel(stat="min")
            < d.sel(stat="p5")
            < d.sel(stat="p10")
            < d.sel(stat="p90")
            < d.sel(stat="p95")
            < d.sel(stat="max")
        )
        assert d.sel(stat="min") < d.sel(stat="mean") < d.sel(stat="max")


def test_get_stats_netcdf(netcdf_location):
    input_path = netcdf_location / "o_fix.nc"

    nf = DataFileStats(
        input_path=input_path, stat_dims=set(["lat", "lon", "nlevsn", "tile", "vtype"])
    )
    dfs = nf.get_stats()

    assert len(dfs) == 1

    df = dfs[0]
    # shape ((4 nlevs x 7 stats), (SoilSat, SoilThick))
    assert df.shape == (28, 2)
    assert sorted(list(df.columns)) == sorted(["SoilSat", "SoilThick"])

    # Sanity check relative values
    ds = df.to_xarray()
    for data_var in ["SoilSat", "SoilThick"]:
        for lev in ds.nlevs:
            d = ds[data_var].sel(nlevs=lev)
            assert (
                d.sel(stat="min")
                <= d.sel(stat="p5")
                <= d.sel(stat="p10")
                <= d.sel(stat="p90")
                <= d.sel(stat="p95")
                <= d.sel(stat="max")
            )


def test_get_stats_netcdf_specify_filetype(netcdf_location):
    input_path = netcdf_location / "o_fix.nc"

    nf = DataFileStats(
        input_path=input_path,
        stat_dims=set(["lat", "lon", "nlevsn", "tile", "vtype"]),
        filetype=DataFileType.NETCDF,
    )
    dfs = nf.get_stats()

    assert len(dfs) == 1


def test_get_stats_netcdf_specify_wrong_filetype_fails(grib_location):
    input_path = grib_location / "model_output_data_spectral.grb2"

    nf = DataFileStats(
        input_path=input_path,
        stat_dims=set(["lat", "lon", "nlevsn", "tile", "vtype"]),
        filetype=DataFileType.NETCDF,
    )
    with pytest.raises(OSError) as exceptinfo:
        nf.get_stats()

    assert "NetCDF: Unknown file format" in str(exceptinfo.value)


def test_get_stats_netcdf_gg(netcdf_location):
    input_path = netcdf_location / "o_gg.nc"

    nf = DataFileStats(
        input_path=input_path, stat_dims=["lat", "lon", "nlevsn", "tile", "vtype"]
    )
    dfs = nf.get_stats()

    assert len(dfs) == 1

    df = dfs[0]
    # shape ((4 nlevs x 7 stats), (SoilMoist, slwML, timestp))
    assert df.shape == (56, 3)
    assert sorted(list(df.columns)) == sorted(["SoilMoist", "slwML", "timestp"])

    # Sanity check relative values
    ds = df.to_xarray()
    for data_var in ["SoilMoist", "slwML"]:
        for lev in ds.nlevs:
            for t in range(2):
                d = ds[data_var].sel(nlevs=lev).isel(time=t)
                assert (
                    d.sel(stat="min")
                    <= d.sel(stat="p5")
                    <= d.sel(stat="p10")
                    <= d.sel(stat="p90")
                    <= d.sel(stat="p95")
                    <= d.sel(stat="max")
                )


def test_get_stats_unknown_stat_raises(netcdf_location):
    input_path = netcdf_location / "o_fix.nc"
    gf = DataFileStats(input_path=input_path, stat_names=set(["x90"]))

    with pytest.raises(ValueError):
        gf.get_stats()


def test_get_stats_keeps_stats(netcdf_location):
    input_path = netcdf_location / "o_fix.nc"
    gf = DataFileStats(input_path=input_path)
    dfs = gf.get_stats()

    df_ret = dfs[0]
    df_kept = gf._stats[0]
    df_kept_2 = gf.get_stats()[0]

    assert df_ret is df_kept
    assert df_kept_2 is df_kept


def test_get_stats_unknown_filetype_fails():
    wrong_format_file_dir = Path(__file__).parent.resolve() / "namelists"
    input_path = wrong_format_file_dir / "array_1.nml"
    dfs = DataFileStats(input_path=input_path)

    with pytest.raises(ValueError) as exceptinfo:
        dfs.get_stats()

    assert "Unable to determine data file type" in str(exceptinfo.value)
    assert "namelists/array_1.nml" in str(exceptinfo.value)
