# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
import pandas as pd
import pytest

from ifsbench import DarshanReport, read_files_from_darshan, write_files_from_darshan


@pytest.fixture(scope="module", name="here")
def fixture_here():
    """Parent directory for tests"""
    return Path(__file__).parent


def test_darshanreport_from_parser_log(here):
    """Verify that darshan-parser log is read correctly."""
    report = DarshanReport(here / "darshan.log")

    # Records loaded and available?
    assert len(report.records) == 3
    for module, count in {"POSIX": 16362, "STDIO": 8904, "LUSTRE": 1322}.items():
        assert isinstance(report.records[module], pd.DataFrame)
        assert isinstance(report.name_records[module], dict)
        assert len(report.records[module]) == count

    # Anything else raises an exception?
    with pytest.raises(KeyError):
        _ = report.records["foo"]
    with pytest.raises(KeyError):
        _ = report.name_records["foo"]


def test_darshanreport_read_files(here):
    """Verify that list of read files is obtained correctly from
    Darshan report."""
    report = DarshanReport(here / "darshan.log")
    read_files = read_files_from_darshan(report)
    assert isinstance(read_files, set)
    assert len(read_files) == 33


def test_darshanreport_write_files(here):
    """Verify that list of write files is obtained correctly from
    Darshan report."""
    report = DarshanReport(here / "darshan.log")
    write_files = write_files_from_darshan(report)
    assert isinstance(write_files, set)
    assert len(write_files) == 38
