# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
ifsbench: IFS benchmark and testing utilities in Python

This package contains Python utilities to run and benchmark the IFS.
"""

from importlib.metadata import version, PackageNotFoundError

from ifsbench.application import * # noqa
from ifsbench.arch import * # noqa
from ifsbench.cli import * # noqa
from ifsbench.config_mixin import * # noqa
from ifsbench.config_utils import * # noqa
from ifsbench.darshanreport import * # noqa
from ifsbench.drhook import * # noqa
from ifsbench.env import * # noqa
from ifsbench.files import * # noqa
from ifsbench.gribfile import * # noqa
from ifsbench.ifs import * # noqa
from ifsbench.job import * # noqa
from ifsbench.launcher import * # noqa
from ifsbench.logging import * # noqa
from ifsbench.namelist import * # noqa
from ifsbench.nodefile import * # noqa
from ifsbench.paths import * # noqa
from ifsbench.runrecord import * # noqa
from ifsbench.util import * # noqa

try:
    __version__ = version("ifsbench")
except PackageNotFoundError:
    # package is not installed
    pass
