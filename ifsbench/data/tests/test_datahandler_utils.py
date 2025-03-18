# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest

from ifsbench.data.datahandler_utils import DataHandlers, DataHandlerLookup
from ifsbench.data.extracthandler import ExtractHandler
from ifsbench.data.namelisthandler import NamelistHandler
from ifsbench.data.renamehandler import RenameHandler


@pytest.mark.parametrize(
    'handlername, handlertype',
    [
        ('ExtractHandler', ExtractHandler),
        ('NamelistHandler', NamelistHandler),
        ('RenameHandler', RenameHandler),
    ],
)
def test_datahandler_utils_from_name(handlername, handlertype):

    lookup_type = DataHandlerLookup[handlername]

    assert lookup_type == handlertype


@pytest.mark.parametrize(
    'handlername, handlertype',
    [
        (DataHandlers.EXTRACT, ExtractHandler),
        (DataHandlers.NAMELIST, NamelistHandler),
        (DataHandlers.RENAME, RenameHandler),
    ],
)
def test_datahandler_utils_from_enum(handlername, handlertype):

    lookup_type = DataHandlerLookup[handlername]

    assert lookup_type == handlertype
