# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Test :any:`IFS` and adjacent classes
"""

import datetime
from pathlib import Path

import pandas as pd
import pytest
from ifsbench import NODEFile

def nodelist_path():
    """Return the path to the nodefiles directory."""
    main_path = Path(__file__).parent.resolve()

    return main_path/'nodefiles'


@pytest.mark.parametrize(
    'node_path,timestamp',
    (
        (nodelist_path()/'nodefile_default', datetime.datetime(2022, 12, 8, 10, 40, 51)),
        (nodelist_path()/'nodefile_pred_corr', datetime.datetime(2022, 12, 8, 10, 40, 51)),
    )
)
def test_nodefile_timestamp(node_path, timestamp):
    """
    Test that the output of the "timestamp" method matches the timestamp in the
    nodefile.
    """
    nodefile = NODEFile(node_path)

    assert nodefile.timestamp == timestamp

@pytest.mark.parametrize(
    'node_path,nrows, ncolumns',
    (
        (nodelist_path()/'nodefile_default', 26, 5),
        (nodelist_path()/'nodefile_pred_corr', 26, 10),
    )
)
def test_spectral_norms(node_path, nrows, ncolumns):
    """
    Test the spectral_norms property against some reference values.
    """
    nodefile = NODEFile(node_path)

    norms = nodefile.spectral_norms

    # Verify that we get a pandas DataFrame and not something else.
    assert isinstance(norms, pd.DataFrame)

    # For the moment, just compare the shape of the DataFrame to some reference
    # values. In the future, we should probably test against the actual values.
    assert norms.shape == (nrows, ncolumns)

@pytest.mark.parametrize(
    'node_path,nrows, ncolumns',
    (
        (nodelist_path()/'nodefile_default', 26, 24),
        (nodelist_path()/'nodefile_pred_corr', 26, 24),
    )
)
def test_grid_norms(node_path, nrows, ncolumns):
    nodefile = NODEFile(node_path)

    norms = nodefile.gridpoint_norms

    assert isinstance(norms, pd.DataFrame)

    assert norms.shape == (nrows, ncolumns)

@pytest.mark.parametrize(
    'value, expected',
    (
        ('0.1e-2', 0.001),
        ('0.1-2', 0.001),
        ('-0.1', -0.1),
    )
)
def test_sanitize_value(value, expected):
    """ Test correct sanitisation to standard scientific format. """
    assert expected == pd.to_numeric(NODEFile._sanitise_float(value))
