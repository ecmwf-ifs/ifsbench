# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import pathlib
from typing import List

import pytest

import pandas as pd

from ifsbench.results import EnsembleStats


INDEX = ['Step 0', 'Step 1']
COLUMNS = ['2m temperature', 'pressure']


def build_frames() -> List[pd.DataFrame]:
    return [
        pd.DataFrame([[293, 1010], [294, 1008]], index=INDEX, columns=COLUMNS),
        pd.DataFrame([[296, 1012], [291, 1009]], index=INDEX, columns=COLUMNS),
        pd.DataFrame([[296, 1014], [292, 1005]], index=INDEX, columns=COLUMNS),
        pd.DataFrame([[295, 1008], [294, 1008]], index=INDEX, columns=COLUMNS),
    ]


def test_from_data():
    in_data = build_frames()

    es = EnsembleStats(frames=in_data)

    for i, df in enumerate(es.frames):
        pd.testing.assert_frame_equal(df, in_data[i])


def test_dump_config():
    in_data = build_frames()
    es = EnsembleStats(frames=in_data)

    conf = es.dump_config()

    read_es = EnsembleStats.from_config(conf)

    for i, df in enumerate(in_data):
        pd.testing.assert_frame_equal(read_es.frames[i], df)


def test_from_config_inline_data():
    # prepare config dict
    in_data = build_frames()
    prep = EnsembleStats(frames=in_data)
    conf = prep.dump_config()

    # Create new object from config.
    es = EnsembleStats.from_config(conf)

    for i, df in enumerate(es.frames):
        pd.testing.assert_frame_equal(df, in_data[i])


def test_from_config_invalid_fails():

    with pytest.raises(ValueError) as exceptinfo:
        EnsembleStats.from_config(
            {
                'parrot': 'dead',
            }
        )



def test_calc_stats_min():
    in_data = build_frames()
    es = EnsembleStats(frames=in_data)

    result = es.calc_stats('min')

    assert len(result) == 1
    assert 'min' in result
    expected = pd.DataFrame([[293, 1008], [291, 1005]], index=INDEX, columns=COLUMNS)
    pd.testing.assert_frame_equal(result['min'], expected)


def test_calc_stats_list():
    in_data = build_frames()
    es = EnsembleStats(frames=in_data)
    stats = ['min', 'p10', 'mean', 'P50', 'p90', 'max', 'std']

    ensemble_stats = es.calc_stats(stats)

    # Expected frames per stat
    df_min = pd.DataFrame([[293, 1008], [291, 1005]], index=INDEX, columns=COLUMNS)
    df_p10 = pd.DataFrame(
        [[293.6, 1008.6], [291.3, 1005.9]], index=INDEX, columns=COLUMNS
    )
    df_mean = pd.DataFrame(
        [[295.0, 1011], [292.75, 1007.5]], index=INDEX, columns=COLUMNS
    )
    df_p50 = pd.DataFrame(
        [[295.5, 1011.0], [293, 1008.0]], index=INDEX, columns=COLUMNS
    )
    df_p90 = pd.DataFrame(
        [[296.0, 1013.4], [294.0, 1008.7]], index=INDEX, columns=COLUMNS
    )
    df_max = pd.DataFrame([[296, 1014], [294, 1009]], index=INDEX, columns=COLUMNS)
    df_std = pd.DataFrame(
        [[1.22474, 2.2360679], [1.299038, 1.500]], index=INDEX, columns=COLUMNS
    )
    expected = {
        'min': df_min,
        'p10': df_p10,
        'mean': df_mean,
        'P50': df_p50,
        'p90': df_p90,
        'max': df_max,
        'std': df_std,
    }

    assert len(ensemble_stats) == len(expected)
    for key, value in expected.items():
        assert key in ensemble_stats
        pd.testing.assert_frame_equal(ensemble_stats[key], value)


def test_calc_stats_unsupported_fails():
    es = EnsembleStats(frames=build_frames())

    with pytest.raises(ValueError) as exceptinfo:
        es.calc_stats('parrot')

    expected = 'Unknown stat: parrot. Supported'
    assert expected in str(exceptinfo.value)


def test_calc_stats_percentile_over_100_fails():
    es = EnsembleStats(frames=build_frames())

    with pytest.raises(ValueError) as exceptinfo:
        es.calc_stats('p101')

    expected = 'Percentile has to be in [0, 100], got 101.'
    assert str(exceptinfo.value) == expected
