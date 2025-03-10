# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
from types import MappingProxyType

from ifsbench.data.extracthandler import ExtractHandler
from ifsbench.data.namelisthandler import NamelistHandler
from ifsbench.data.renamehandler import RenameHandler

__all__ = ['DataHandlers', 'DataHandlerLookup']

class DataHandlers(str, Enum):
    EXTRACT = ExtractHandler.__name__
    NAMELIST = NamelistHandler.__name__
    RENAME = RenameHandler.__name__


DataHandlerLookup = MappingProxyType({
    DataHandlers.EXTRACT: ExtractHandler,
    DataHandlers.NAMELIST: NamelistHandler,
    DataHandlers.RENAME: RenameHandler,
})
