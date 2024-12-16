# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pathlib
import shutil

from .datahandler import DataHandler
from ..logging import debug

__all__ = ['ExtractHandler']


class ExtractHandler(DataHandler):
    """
    DataHandler that extracts a given archive to a specific directory.
    """

    def __init__(self, archive_path, target_dir=None):
        """
        Initialise the handler.

        Parameters
        ----------
        archive_path: str or `pathlib.Path`
            The path to the archive that will be extracted. If a relative path
            is given, this will be relative to the `wdir` argument in `execute`.

        target_dir: str, `pathlib.Path` or `None`
            The directory to where the archive will be unpacked. If a relative path
            is given, this will be relative to the `wdir` argument in `execute`.
            If None is given, this will re extracted to `wdir`.
        """

        self._archive_path = pathlib.Path(archive_path)
        if target_dir is None:
            self._target_dir = None
        else:
            self._target_dir = pathlib.Path(target_dir)

    def execute(self, wdir, **kwargs):
        target_dir = wdir
        if self._target_dir is not None:
            if self._target_dir.is_absolute():
                target_dir = self._target_dir
            else:
                target_dir = wdir/self._target_dir

        debug(f"Unpack archive {self._archive_path} to {target_dir}.")
        shutil.unpack_archive(self._archive_path, target_dir)
