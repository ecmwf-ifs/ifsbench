# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import auto, Enum
from pathlib import Path
import re
import shutil

from .datahandler import DataHandler
from ..logging import debug

__all__ = ['RenameHandler']

class RenameHandler(DataHandler):
    """
    DataHandler specialisation that can move/rename files by using regular
    expressions (as in re.sub).
    """

    class RenameMode(Enum):
        """
        Enumeration of available rename operations.

        Attributes
        ----------
        COPY :
            Copy the file from its current place to the new location.
        SYMLINK :
            Create a symlink in the new location, pointing to its current
            location.
        MOVE :
            Move the file from its current place to the new location.
        """
        COPY = auto()
        SYMLINK = auto()
        MOVE = auto()

    def __init__(self, pattern, repl, mode=RenameMode.SYMLINK):
        """
        Initialise the handler.

        Parameters
        ----------
        pattern: str
            The pattern that will be replaced. Corresponds to `pattern` in
            `re.sub`.

        repl: str
            The replacement pattern. Corresponds to `repl` in `re.sub`.

        mode:   `RenameHandler.RenameMode`
            Specifies how the renaming is done (copy, move, symlink).

        mode:   `RenameHandler.RenameMode`
            Specifies how the renaming is done (copy, move, symlink).
        """
        self._pattern = str(pattern)
        self._repl = str(repl)
        self._mode = mode


    def execute(self, wdir, **kwargs):
        # We create a dictionary first, that stores the paths that will be
        # modified.
        path_mapping = {}

        for f in list(wdir.rglob('*')):
            if f.is_dir():
                continue

            dest = Path(re.sub(self._pattern, self._repl, str(f.relative_to(wdir))))
            dest = (wdir/dest).resolve()

            if f != dest:
                path_mapping[f] = dest

        # Check that we don't end up with two initial files being renamed to
        # the same file. Crash if this is the case.
        if len(set(path_mapping.keys())) != len(set(path_mapping.values())):
            raise RuntimeError("Renaming would cause two different files to be given the same name!")

        for source, dest in path_mapping.items():
            # Crash if we are renaming one of the files to a path that is also
            # the "source" for another renaming.
            if dest in path_mapping:
                raise RuntimeError(f"Can't move {source} to {dest} as there is a cyclical dependency!")

            # Delete whatever resides at dest at the moment (whether it's a
            # file or a directory).
            if dest.exists():
                debug(f"Delete existing file/directory {dest} before renaming.")
                try:
                    shutil.rmtree(dest)
                except NotADirectoryError:
                    dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)

            if self._mode == self.RenameMode.COPY:
                debug(f"Copy {source} to {dest}.")

                shutil.copy(source, dest)
            elif self._mode == self.RenameMode.SYMLINK:
                debug(f"Symlink {source} to {dest}.")

                dest.symlink_to(source)
            elif self._mode == self.RenameMode.MOVE:
                debug(f"Move {source} to {dest}.")

                source.rename(dest)
