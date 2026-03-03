# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
from functools import cached_property
from pathlib import Path
import os
import re
import shutil
from typing import Union

from pydantic import computed_field

from ifsbench.data.datahandler import DataHandler
from ifsbench.logging import debug

__all__ = ['RenameHandler', 'RenameMode']


class RenameMode(str, Enum):
    """
    Enumeration of available rename operations.
    """

    #: Copy the file from its current place to the new location.
    COPY = 'copy'

    #: Create a symlink in the new location, pointing to its current location.
    SYMLINK = 'symlink'

    #: Move the file from its current place to the new location.
    MOVE = 'move'


class RenameHandler(DataHandler):
    """
    DataHandler specialisation that can move/rename files by using regular
    expressions (as in :any:`re.sub`).

    Parameters
    ----------
    pattern: str or :any:`re.Pattern`
        The pattern that will be replaced. Corresponds to ``pattern`` in
        :any:`re.sub`.

    repl: str
        The replacement pattern. Corresponds to ``repl`` in :any:`re.sub`.

    mode: :class:`RenameMode`
        Specifies how the renaming is done (copy, move, symlink).
    """

    pattern: str
    repl: str
    mode: RenameMode = RenameMode.SYMLINK

    @computed_field
    @cached_property
    def _pattern(self) -> re.Pattern:
        return re.compile(self.pattern)

    def execute(self, wdir: Union[str, Path], **kwargs) -> None:
        wdir = Path(wdir)

        # We create a dictionary first, that stores the paths that will be
        # modified.
        path_mapping = {}

        for f in wdir.rglob('*'):
            if f.is_dir():
                continue

            dest = self._pattern.sub(self.repl, str(f.relative_to(wdir)))
            dest = Path(os.path.normpath(wdir / dest))

            if f != dest:
                path_mapping[f] = dest

        # Check that we don't end up with two initial files being renamed to
        # the same file. Crash if this is the case.
        if len(set(path_mapping.keys())) != len(set(path_mapping.values())):
            raise RuntimeError(
                'Renaming would cause two different files to be given the same name!'
            )

        for source, dest in path_mapping.items():
            # Crash if we are renaming one of the files to a path that is also
            # the "source" for another renaming.
            if dest in path_mapping:
                raise RuntimeError(
                    f"Can't move {source} to {dest} as there is a cyclical dependency!"
                )

            # Delete whatever resides at dest at the moment (whether it's a
            # file or a directory).
            if dest.exists():
                debug(f'Delete existing file/directory {dest} before renaming.')
                try:
                    shutil.rmtree(dest)
                except NotADirectoryError:
                    dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)

            if self.mode == RenameMode.COPY:
                debug(f'Copy {source} to {dest}.')

                shutil.copy(source, dest)
            elif self.mode == RenameMode.SYMLINK:
                debug(f'Symlink {source} to {dest}.')

                dest.symlink_to(source)
            elif self.mode == RenameMode.MOVE:
                debug(f'Move {source} to {dest}.')

                source.rename(dest)
