# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import auto, Enum
import pathlib

import f90nml

from .datahandler import DataHandler
from ..logging import debug, info


__all__ = ['NamelistOverride', 'NamelistHandler']


class NamelistOverride:
    """
    Specify changes that will be applied to a namelist.
    """
    class NamelistOperation(Enum):
        SET = auto()
        APPEND = auto()
        DELETE = auto()

    def __init__(self, key, mode, value=None):
        """
        Parameters
        ----------
        key: str or iterable of str
            The namelist entry that will be modified. Can be either a string
            where '/' separates the namelist name and the entry key or an iterable
            of strings of length two.

        mode: NamelistOverride.NamelistOperation
            What kind of operation is specified. Can be
                * Set a certain entry.
                * Append to an array entry.
                * Delete an entry.

        value:
            The value that is set (SET operation) or appended (APPEND).
        """

        if isinstance(key, str):
            self._keys = key.split('/')
        else:
            self._keys = tuple(key)

        if len(self._keys) != 2:
            raise ValueError("The key object must be of length two.")

        self._mode = mode
        self._value = value

        if self._value is None:
            if self._mode in (self.NamelistOperation.SET, self.NamelistOperation.APPEND):
                raise ValueError("The new value must not be None!")

    def apply(self, namelist):
        """
        Apply the stored changes to a namelist.

        Parameters
        ----------
        namelist: f90nml.Namelist
            The namelist to which the changes are applied.
        """

        if self._keys[0] not in namelist:
            if self._mode == self.NamelistOperation.DELETE:
                return

            namelist[self._keys[0]] = {}

        namelist = namelist[self._keys[0]]
        key = self._keys[-1]

        if self._mode == self.NamelistOperation.SET:
            debug(f"Set namelist entry {str(self._keys)} = {str(self._value)}.")
            namelist[key] = self._value
        elif self._mode == self.NamelistOperation.APPEND:
            if key not in namelist:
                namelist[key] = []

            if not hasattr(namelist[key], 'append'):
                raise ValueError("Values can only be appended to arrays!")

            # f90nml doesn't seem to do any kind of checking, so we could
            # create arrays in the namelist where the entries have different
            # types.
            # This will most likely cause issues, so we verify here, that
            # the array entries have the same type.
            if len(namelist[key]) > 0:
                type_list = type(namelist[key][0])
                type_value = type(self._value)

                if type_list != type_value:
                    raise ValueError("The given value must have the same type as existing array entries!")

            debug(f"Append {str(self._value)} to namelist entry {str(self._keys)}.")

            namelist[key].append(self._value)

        elif self._mode == self.NamelistOperation.DELETE:
            if key in namelist:
                debug(f"Delete namelist entry {str(self._keys)}.")
                del namelist[key]

class NamelistHandler(DataHandler):
    """
    DataHandler specialisation that can modify Fortran namelists.
    """

    def __init__(self, input_path, output_path, overrides):
        """
        Initialise the handler.

        Parameters
        ----------
        input_path: str or `pathlib.Path`
            The path to the namelist that will be modified. If a relative path
            is given, this will be relative to the `wdir` argument in `execute`.

        output_path: str, `pathlib.Path` or `None`
            The path to which the updated namelist will be written. If a relative path
            is given, this will be relative to the `wdir` argument in `execute`.
            If None is given, this will re extracted to `wdir`.

        overrides: iterable of NamelistOverride
            The NamelistOverrides that will be applied.
        """

        self._input_path = pathlib.Path(input_path)
        self._output_path = pathlib.Path(output_path)

        self._overrides = list(overrides)
        for override in self._overrides:
            if not isinstance(override, NamelistOverride):
                raise ValueError("Namelist overrides must be NamelistOverride objects!")

    def execute(self, wdir, **kwargs):
        if self._input_path.is_absolute():
            input_path = self._input_path
        else:
            input_path = wdir/self._input_path

        # Do nothing if the input namelist doesn't exist.
        if not input_path.exists():
            info(f"Namelist {input_path} doesn't exist.")
            return

        if self._output_path.is_absolute():
            output_path = self._output_path
        else:
            output_path = wdir/self._output_path

        debug(f"Modify namelist {input_path}.")
        namelist = f90nml.read(input_path)

        for override in self._overrides:
            override.apply(namelist)

        namelist.write(output_path, force=True)
