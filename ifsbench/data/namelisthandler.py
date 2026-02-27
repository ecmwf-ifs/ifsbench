# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
import pathlib
from typing import List, Union

from pydantic import model_validator
from typing_extensions import Self

import f90nml

from ifsbench.serialisation_mixin import SerialisationMixin
from ifsbench.data.datahandler import absolutise_path, DataHandler
from ifsbench.logging import debug, info
from ifsbench.namelist import SanitiseMode, sanitise_namelist


__all__ = [
    'NamelistOverride',
    'NamelistHandler',
    'NamelistOperation',
    'SanitiseMode',
    'NamelistSanitiseHandler',
]


class NamelistOperation(str, Enum):
    SET = 'set'
    APPEND = 'append'
    DELETE = 'delete'


class NamelistOverride(SerialisationMixin):
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
                raise ValueError('The new value must not be None!')
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
            debug(f'Set namelist entry {self.namelist}/{self.entry} = {str(self.value)}.')
            namelist[key] = self.value
        elif self.mode == NamelistOperation.APPEND:
            if key not in namelist:
                namelist[key] = []

            if not hasattr(namelist[key], 'append'):
                raise ValueError('Values can only be appended to arrays!')

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
                        'The given value must have the same type as existing array entries!'
                    )

            debug(f'Append {str(self.value)} to namelist entry {self.namelist}/{self.entry}.')

            namelist[key].append(self.value)

        elif self.mode == NamelistOperation.DELETE:
            if key in namelist:
                debug(f'Delete namelist entry {self.namelist}/{self.entry}.')
                del namelist[key]


class NamelistHandler(DataHandler):
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
    overrides: List[NamelistOverride]

    def execute(self, wdir: Union[str, pathlib.Path], **kwargs):
        input_path = absolutise_path(wdir, self.input_path)

        # Do nothing if the input namelist doesn't exist.
        if not input_path.exists():
            info(f"Namelist {input_path} doesn't exist.")
            return

        output_path = absolutise_path(wdir, self.output_path)

        debug(f'Modify namelist {input_path}.')
        namelist = f90nml.read(input_path)

        namelist.uppercase = True
        namelist.end_comma = True

        for override in self.overrides:
            override.apply(namelist)

        # If output_path exists and is a symlink, f90nml will just overwrite
        # the target of the namelist. This is not ideal, therefore we delete
        # output_path, if it is a symlink.
        if output_path.is_symlink():
            output_path.unlink()

        namelist.write(output_path, force=True)


class NamelistSanitiseHandler(DataHandler):
    """
    DataHandler specialisation that can sanitise Fortran namelists.
    Sanitise means that duplicate entries in a namelist will be resolved,
    using different resolution strategies.
    """

    #: The path to the namelist that will be modified. If a relative path is
    #: given, this will be relative to the ``wdir`` argument in :meth:`execute`.
    input_path: pathlib.Path

    #: The path to which the updated namelist will be written. If a relative
    #: path is given, this will be relative to the ``wdir`` argument in
    #: :meth:`execute`.
    output_path: pathlib.Path

    #: The sanitising/merging strategy that is used. See :class:`SanitiseMode`
    #: for the different options.
    mode: SanitiseMode = SanitiseMode.MERGE_LAST

    def execute(self, wdir: pathlib.Path, **kwargs):
        input_path = absolutise_path(wdir, self.input_path)

        # Do nothing if the input namelist doesn't exist.
        if not input_path.exists():
            info(f"Namelist {input_path} doesn't exist.")
            return

        output_path = absolutise_path(wdir, self.output_path)

        debug(f'Sanitise namelist {input_path} using sanitise mode {self.mode}.')

        namelist = f90nml.read(input_path)

        namelist.uppercase = True
        namelist.end_comma = True

        namelist = sanitise_namelist(nml=namelist, merge_strategy=self.mode, mode='auto')

        namelist.write(output_path, force=True)
