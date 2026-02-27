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
import pytest

from ifsbench import DrHookRecord


def get_data(df, routine, metric):
    return (df.loc[df['routine'] == routine][metric]).iloc[0]


def get_metadata(df, metric):
    return df.loc[0][metric]


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve()


@pytest.fixture(name='drhook_profiles')
def fixture_experiment_files(here):
    """Return the full path to the directory with dummy experiment files"""
    return here / 'drhook_profiles'


@pytest.mark.parametrize('batch_size', [2, 4, 6, 15, 20, 1000])
def test_drhook_from_raw(drhook_profiles, batch_size):
    """
    Test parsing of drhook profiles from raw (in dependence of batch size).
    """
    drhook_record = DrHookRecord.from_raw(f'{drhook_profiles}/drhook.*', batch_size=batch_size)
    data = drhook_record.data
    metadata = drhook_record.metadata

    assert get_data(data, 'ADVECTION_LOOP', 'avgTimeTotal') == pytest.approx(2.95975, 0.01)
    assert get_data(data, 'READWIND', 'avgPercent') == pytest.approx(19.088125, 0.01)
    assert int(get_metadata(metadata, 'nprocs')) == 16
    assert float(get_metadata(metadata, 'maxtime')) == pytest.approx(6.7, 0.01)
