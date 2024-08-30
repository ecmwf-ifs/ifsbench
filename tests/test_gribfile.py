import os
from pathlib import Path
import pytest

import numpy as np
import xarray as xr

from ifsbench import gribfile
from ifsbench import (
    GribFile,
    NoGribModification,
    UniformGribNoiseFromMetadata,
    modify_grib_file,
)


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / 'gribfiles'


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason='could not import cfgrib, likely missing eccodes.',
)
def test_get_stats_pressurelevels_single_dataset(here):
    input_path = here / 'model_output_data_pl.grb2'

    gf = GribFile(input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 1

    df = dfs[0]
    # shape ((2step x 2 level x 7 stats), (time, valid_time, u, v))
    assert df.shape == (28, 4)
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 'u', 'v'])

    # Sanity check relative values
    ds = df.to_xarray()
    for data_var in ['u', 'v']:
        for s in ds.step:
            for p in ds.isobaricInhPa:
                print(f'{data_var} - {s} - {p}')
                d = ds[data_var].sel(step=s, isobaricInhPa=p)
                assert (
                    d.sel(stat='min')
                    < d.sel(stat='p5')
                    < d.sel(stat='p10')
                    < d.sel(stat='mean')
                    < d.sel(stat='p90')
                    < d.sel(stat='p95')
                    < d.sel(stat='max')
                )


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason='could not import cfgrib, likely missing eccodes.',
)
def test_get_stats_two_datasets(here):
    input_path = here / 'model_output_data_rad.grb2'

    gf = GribFile(input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 2

    df = dfs[0]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ttr))
    assert df.shape == (14, 4)
    assert sorted(list(df.columns)) == sorted(
        ['time', 'valid_time', 'ttr', 'nominalTop']
    )

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
        d = ds['ttr'].sel(step=s)
        assert (
            d.sel(stat='min')
            < d.sel(stat='p5')
            < d.sel(stat='p10')
            < d.sel(stat='mean')
            < d.sel(stat='p90')
            < d.sel(stat='p95')
            < d.sel(stat='max')
        )

    df = dfs[1]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ssr))
    assert df.shape == (14, 4)
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 'ssr', 'surface'])

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
        d = ds['ssr'].sel(step=s)
        assert (
            d.sel(stat='min')
            <= d.sel(stat='p5')
            <= d.sel(stat='p10')
            < d.sel(stat='mean')
            < d.sel(stat='p90')
            < d.sel(stat='p95')
            <= d.sel(stat='max')
        )


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason='could not import cfgrib, likely missing eccodes.',
)
def test_get_stats_spectral(here):
    input_path = here / 'model_output_data_spectral.grb2'

    gf = GribFile(input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 4

    df = dfs[0]
    # shape ((19 levels x 7 stats), (time, valid_time, step, t))
    assert df.shape == (133, 4)
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 't', 'step'])

    # Sanity check relative values
    ds = df.to_xarray()
    for level in ds.hybrid:
        d = ds['t'].sel(hybrid=level)
        print(f'level: {level}, data:\n{d}')
        # In this case, p90 < mean, therefore splitting the checks.
        assert (
            d.sel(stat='min')
            < d.sel(stat='p5')
            < d.sel(stat='p10')
            < d.sel(stat='p90')
            < d.sel(stat='p95')
            < d.sel(stat='max')
        )
        assert d.sel(stat='min') < d.sel(stat='mean') < d.sel(stat='max')


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason='could not import cfgrib, likely missing eccodes.',
)
def test_get_stats_unknown_stat_raises(here):
    stat_names = gribfile._STAT_NAMES
    input_path = here / 'model_output_data_rad.grb2'
    gf = GribFile(input_path)

    gribfile._STAT_NAMES = ['x90']

    with pytest.raises(ValueError):
        gf.get_stats()

    gribfile._STAT_NAMES = stat_names


@pytest.mark.skipif(
    not gribfile.CFGRIB_AVAILABLE,
    reason='could not import cfgrib, likely missing eccodes.',
)
def test_get_stats_keeps_stats(here):
    input_path = here / 'model_output_data_pl.grb2'
    gf = GribFile(input_path)
    dfs = gf.get_stats()

    df_ret = dfs[0]
    df_kept = gf._stats[0]

    assert df_ret is df_kept


def _read_grib(input_path: str, short_name: str) -> xr.Dataset:
    ds = xr.open_dataset(
        input_path,
        engine='cfgrib',
        backend_kwargs={
            'filter_by_keys': {'shortName': short_name},
            'indexpath': '',
            'read_keys': ['packingError'],
        },
    )
    return ds


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason='could not import pygrib or cfgrib, likely missing eccodes.',
)
def test_modify_grib_file(here, tmp_path):
    noise_scale = 1.0001
    input_path = here / 'model_input_data_stl.grb'
    output_path = tmp_path / 'out.grib'
    params = ['stl1', 'stl2']

    no_noise = NoGribModification()
    uniform_noise = UniformGribNoiseFromMetadata(
        noise_param='packingError', noise_scale=noise_scale
    )
    noise_config = dict.fromkeys(params, uniform_noise)

    modify_grib_file(
        input_path,
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
    packing_error = ds_ref[param].attrs['GRIB_packingError']

    assert abs(comp_max) > 0
    assert abs(comp_min) > 0
    assert abs(comp_max) <= 2 * packing_error * noise_scale
    assert abs(comp_min) <= 2 * packing_error * noise_scale

    # confirm that stl3 has not been modified
    param = 'stl3'
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])

    assert comp_max == 0
    assert comp_min == 0


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason='could not import pygrib or cfgrib, likely missing eccodes.',
)
def test_modify_grib_fractionparam(here, tmp_path):
    noise_scale = 1.001
    input_path = here / 'model_input_data_fractionparam.grb'
    output_path = tmp_path / 'out.grib'
    params = ['cc', 'crwc']

    uniform_noise = UniformGribNoiseFromMetadata(
        noise_param='packingError', noise_scale=noise_scale
    )

    modify_grib_file(input_path, output_path, base_modification=uniform_noise)

    # confirm that cc has been modified and clipped to [0,1]
    param = params[0]
    ds_ref = _read_grib(input_path, param)
    ds_mod = _read_grib(output_path, param)
    ds_comp = ds_mod - ds_ref
    comp_max = np.nanmax(ds_comp[param])
    comp_min = np.nanmin(ds_comp[param])
    packing_error = ds_ref[param].attrs['GRIB_packingError']

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
    reason='could not import pygrib or cfgrib, likely missing eccodes.',
)
def test_modify_grib_output_exists(here, tmp_path):
    input_path = here / 'model_input_data_stl.grb'
    output_path = tmp_path / 'out.grib'

    no_noise = NoGribModification()

    # Create the output and set its mtime and atime to the past.
    open(output_path, 'w').close()
    os.utime(output_path, ns=(1000, 1000))

    modify_grib_file(input_path, output_path, no_noise)

    # Confirm that file times have not changed and the file is empty,
    # i.e. nothing was written.
    statinfo = os.stat(output_path)
    assert statinfo.st_mtime_ns == 1000
    assert statinfo.st_size == 0


@pytest.mark.skipif(
    not gribfile.PYGRIB_AVAILABLE or not gribfile.CFGRIB_AVAILABLE,
    reason='could not import pygrib or cfgrib, likely missing eccodes.',
)
def test_modify_grib_output_exists_allow_overwrite(here, tmp_path):
    input_path = here / 'model_input_data_stl.grb'
    output_path = tmp_path / 'out.grib'

    no_noise = NoGribModification()

    # Create the output and set its mtime and atime to the past.
    open(output_path, 'w').close()
    os.utime(output_path, ns=(1000, 1000))

    modify_grib_file(input_path, output_path, no_noise, overwrite_existing=True)

    # Confirm that file times have not changed and the file is empty,
    # i.e. nothing was written.
    statinfo = os.stat(output_path)
    assert statinfo.st_mtime_ns > 1000
    assert statinfo.st_size > 0
