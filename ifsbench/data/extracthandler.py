# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pathlib
import shutil
from typing import Dict, Optional, Union

from typing_extensions import Literal

from ifsbench.data.datahandler import DataHandler
from ifsbench.logging import debug

__all__ = ['ExtractHandler']


class ExtractHandler(DataHandler):
    """
    DataHandler that extracts a given archive to a specific directory.

    Parameters
    ----------
    archive_path: str or :any:`pathlib.Path`
        The path to the archive that will be extracted. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    target_dir: str, :any:`pathlib.Path` or None
        The directory where the archive will be unpacked. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.
    """

    handler_type: Literal['ExtractHandler'] = 'ExtractHandler'
    archive_path: str
    target_dir: Optional[str] = None

    @classmethod
    def from_config(cls, config: Dict[str, Optional[str]]) -> 'ExtractHandler':
        eh = cls(**config)
        eh._archive_path = pathlib.Path(eh.archive_path)
        if eh.target_dir is None:
            eh._target_dir = None
        else:
            eh._target_dir = pathlib.Path(eh.target_dir)
        return eh

    def execute(self, wdir: Union[str, pathlib.Path], **kwargs) -> None:
        wdir = pathlib.Path(wdir)

        target_dir = wdir
        if self._target_dir is not None:
            if self._target_dir.is_absolute():
                target_dir = self._target_dir
            else:
                target_dir = wdir / self._target_dir

        debug(f"Unpack archive {self._archive_path} to {target_dir}.")
        shutil.unpack_archive(self._archive_path, target_dir)
