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

from ifsbench.config_mixin import CLASSNAME
from ifsbench.results import ENSEMBLE_DATA_PATH, EnsembleStats


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

    es = EnsembleStats.from_data(in_data)

    for i, df in enumerate(es._raw_data):
        pd.testing.assert_frame_equal(df, in_data[i])


def test_dump_data_to_json(tmp_path: pathlib.Path):
    in_data = build_frames()
    es = EnsembleStats.from_data(in_data)
    out_path = str((tmp_path / 'test_data.json').resolve())
    es.dump_data_to_json(out_path)

    with open(out_path, 'r', encoding='utf-8') as fin:
        data = json.load(fin)

    assert isinstance(data, list)
    assert len(data) == len(in_data)


def test_from_config(tmp_path: pathlib.Path):
    in_data = build_frames()
    conf_path = str((tmp_path / 'test_data.json').resolve())
    prep = EnsembleStats.from_data(in_data)
    prep.dump_data_to_json(conf_path)

    es = EnsembleStats.from_config(
        {
            ENSEMBLE_DATA_PATH: str(conf_path),
        }
    )

    for i, df in enumerate(es._raw_data):
        pd.testing.assert_frame_equal(df, in_data[i])


def test_from_config_no_path_fails():

    with pytest.raises(ValueError) as exceptinfo:
        EnsembleStats.from_config(
            {
                'parrot': 'dead',
            }
        )
    expected = f'missing config entry {ENSEMBLE_DATA_PATH}'
    assert str(exceptinfo.value) == expected


def test_from_config_invalid_fails():

    with pytest.raises(ValueError) as exceptinfo:
        EnsembleStats.from_config(
            {
                ENSEMBLE_DATA_PATH: 'nowhere/in/particular',
                'parrot': 'dead',
            }
        )
    expected = 'unexpected entries in config'
    assert expected in str(exceptinfo.value)


def test_dump_config_no_file_empty():
    es = EnsembleStats.from_data(build_frames())

    conf = es.dump_config()

    assert len(conf) == 0


def test_dump_config_from_file_with_class(tmp_path: pathlib.Path):
    prep = EnsembleStats.from_data(build_frames())
    conf_path = str((tmp_path / 'test_data.json').resolve())
    prep.dump_data_to_json(conf_path)

    es = EnsembleStats.from_config(
        {
            ENSEMBLE_DATA_PATH: str(conf_path),
        }
    )

    conf = es.dump_config(with_class=True)

    assert len(conf) == 2
    assert conf[ENSEMBLE_DATA_PATH] == str(conf_path)
    assert conf[CLASSNAME] == 'EnsembleStats'


def test_dump_config_after_dump_data_overwrites_file(tmp_path: pathlib.Path):
    prep = EnsembleStats.from_data(build_frames())
    conf_path = str((tmp_path / 'test_data_in.json').resolve())
    prep.dump_data_to_json(conf_path)

    es = EnsembleStats.from_config(
        {
            ENSEMBLE_DATA_PATH: str(conf_path),
        }
    )

    es.dump_data_to_json((tmp_path / 'test_data_out.json'))

    conf = es.dump_config()

    assert len(conf) == 1
    assert conf[ENSEMBLE_DATA_PATH] == str((tmp_path / 'test_data_out.json'))


def test_calc_stats_min():
    in_data = build_frames()
    es = EnsembleStats.from_data(in_data)

    ensemble_min = es.calc_stats('min')

    mi = pd.MultiIndex.from_tuples([('2m temperature', 'min'), ('pressure', 'min')])
    expected = pd.DataFrame([[293, 1008], [291, 1005]], index=INDEX, columns=mi)
    pd.testing.assert_frame_equal(ensemble_min, expected)


def test_calc_stats_list():
    in_data = build_frames()
    es = EnsembleStats.from_data(in_data)
    stats = ['min', 'p10', 'mean', 'p50', 'p90', 'max', 'std']

    ensemble_stats = es.calc_stats(stats)

    mi = pd.MultiIndex.from_tuples(
        [
            ('2m temperature', 'min'),
            ('2m temperature', 'p10'),
            ('2m temperature', 'mean'),
            ('2m temperature', 'p50'),
            ('2m temperature', 'p90'),
            ('2m temperature', 'max'),
            ('2m temperature', 'std'),
            ('pressure', 'min'),
            ('pressure', 'p10'),
            ('pressure', 'mean'),
            ('pressure', 'p50'),
            ('pressure', 'p90'),
            ('pressure', 'max'),
            ('pressure', 'std'),
        ],
    )
    expected = pd.DataFrame(
        [
            [
                293,
                293.6,
                295.0,
                295.5,
                296.0,
                296,
                1.22474,
                1008,
                1008.6,
                1011.0,
                1011.0,
                1013.4,
                1014,
                2.2360679,
            ],
            [
                291,
                291.3,
                292.75,
                293.0,
                294.0,
                294,
                1.299038,
                1005,
                1005.9,
                1007.5,
                1008.0,
                1008.7,
                1009,
                1.500,
            ],
        ],
        index=INDEX,
        columns=mi,
    )
    pd.testing.assert_frame_equal(ensemble_stats, expected)


def test_calc_stats_unsupported_fails():
    es = EnsembleStats.from_data(build_frames())

    with pytest.raises(ValueError) as exceptinfo:
        es.calc_stats('parrot')

    expected = 'Unknown stat: parrot. Supported'
    assert expected in str(exceptinfo.value)
