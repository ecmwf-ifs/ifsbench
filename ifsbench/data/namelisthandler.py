# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
import pathlib
from typing import Any, Dict, List, Union

from pydantic import model_validator
from typing_extensions import Self

import f90nml

from ifsbench.config_mixin import PydanticConfigMixin
from ifsbench.data.datahandler import DataHandler
from ifsbench.logging import debug, info


__all__ = ['NamelistOverride', 'NamelistHandler', 'NamelistOperation']


class NamelistOperation(Enum):
    SET = 'set'
    APPEND = 'append'
    DELETE = 'delete'


class NamelistOverride(PydanticConfigMixin):
    """
    Specify changes that will be applied to a namelist.

    Parameters
    ----------
    key: str or iterable of str
        The namelist entry that will be modified. Can be either a string
        where '/' separates the namelist name and the entry key or an iterable
        of strings of length two.

    mode: NamelistOperation
        What kind of operation is specified. Can be
            * Set a certain entry.
            * Append to an array entry.
            * Delete an entry.

    value: str or None
        The value that is set (SET operation) or appended (APPEND).
    """

    namelist: str
    entry: str
    mode: NamelistOperation
    value: Union[int, float, str, bool, List, None] = None

    @model_validator(mode='after')
    def validate_value_for_mode(self) -> Self:
        if self.value is None:
            if self.mode in (NamelistOperation.SET, NamelistOperation.APPEND):
                raise ValueError("The new value must not be None!")
        return self

    def apply(self, namelist):
        """
        Apply the stored changes to a namelist.

        Parameters
        ----------
        namelist: :any:`f90nml.namelist.Namelist`
            The namelist to which the changes are applied.
        """

        if self.namelist not in namelist:
            if self.mode == NamelistOperation.DELETE:
                return

            namelist[self.namelist] = {}

        namelist = namelist[self.namelist]
        key = self.entry

        if self.mode == NamelistOperation.SET:
            debug(
                f"Set namelist entry {self.namelist}/{self.entry} = {str(self.value)}."
            )
            namelist[key] = self.value
        elif self.mode == NamelistOperation.APPEND:
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
                type_value = type(self.value)

                if type_list != type_value:
                    raise ValueError(
                        "The given value must have the same type as existing array entries!"
                    )

            debug(
                f"Append {str(self.value)} to namelist entry {self.namelist}/{self.entry}."
            )

            namelist[key].append(self.value)

        elif self.mode == NamelistOperation.DELETE:
            if key in namelist:
                debug(f"Delete namelist entry {self.namelist}/{self.entry}.")
                del namelist[key]


class NamelistHandler(DataHandler, PydanticConfigMixin):
    """
    DataHandler specialisation that can modify Fortran namelists.

    Parameters
    ----------
    input_path: str or :any:`pathlib.Path`
        The path to the namelist that will be modified. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    output_path: str or :any:`pathlib.Path`
        The path to which the updated namelist will be written. If a relative
        path is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    overrides: iterable of :class:`NamelistOverride`
        The NamelistOverrides that will be applied.
    """

    input_path: pathlib.Path
    output_path: pathlib.Path
    overrides: List[Dict[str, Union[str, int]]]

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'NamelistHandler':

        nh = cls(**config)
        nh._input_path = pathlib.Path(nh.input_path)
        nh._output_path = pathlib.Path(nh.output_path)
        nh._overrides = [
            NamelistOverride.from_config(noc) for noc in config['overrides']
        ]
        return nh

    def execute(self, wdir, **kwargs):
        wdir = pathlib.Path(wdir)

        if self._input_path.is_absolute():
            input_path = self._input_path
        else:
            input_path = wdir / self._input_path

        # Do nothing if the input namelist doesn't exist.
        if not input_path.exists():
            info(f"Namelist {input_path} doesn't exist.")
            return

        if self._output_path.is_absolute():
            output_path = self._output_path
        else:
            output_path = wdir / self._output_path

        debug(f"Modify namelist {input_path}.")
        namelist = f90nml.read(input_path)

        for override in self._overrides:
            override.apply(namelist)

        namelist.write(output_path, force=True)
