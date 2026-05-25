# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import List

from ifsbench.launch.launcher import CommandOverride

__all__ = ['CommandWrapOverride']


class CommandWrapOverride(CommandOverride):
    """
    :any:`CommandOverride` implementation that allows appending/prepending to a
    command.

    The resulting command will be
        prepend_cmd + original_command + append_cmd.
    """

    #: List of tokens prepended to the command.
    prepend_cmd: List[str] = []

    #: List of tokens appended to the command.
    append_cmd: List[str] = []

    def override(self, cmd: List[str]) -> List[str]:
        return [*self.prepend_cmd, *cmd, *self.append_cmd]
