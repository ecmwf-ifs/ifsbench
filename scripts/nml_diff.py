#!/usr/bin/env python3

# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import click
import f90nml

from ifsbench import namelist_diff, sanitize_namelist, colors, logger, INFO


def print_neutral(indent, msg, *args, **kwargs):
    logger.log(INFO, ' ' + '  ' * indent + msg, *args, **kwargs)


def print_add(indent, msg, *args, **kwargs):
    logger.log(INFO, colors.OKGREEN % ('+' + '  ' * indent + msg), *args, **kwargs)


def print_sub(indent, msg, *args, **kwargs):
    logger.log(INFO, colors.FAIL % ('-' + '  ' * indent + msg), *args, **kwargs)


def print_value(name, value, indent, printer):
    if value is None:
        return

    if isinstance(value, dict):
        for key, val in value.items():
            print_value(key, val, indent, printer)
    else:
        printer(indent, '%s = %s', name, str(value))


def print_diff(diff, indent=0):
    for group, values in diff.items():
        if isinstance(values, dict):
            print_neutral(indent, '&%s', group)
            print_diff(values, indent + 1)
            print_neutral(indent, '/')
        else:
            assert isinstance(values, tuple)

            if values[0] is None:
                print_group = print_add
            elif values[1] is None:
                print_group = print_sub
            else:
                print_group = print_neutral

            print_group(indent, '&%s', group)
            print_value(group, values[0], indent + 1, print_sub)
            print_value(group, values[1], indent + 1, print_add)
            print_group(indent, '/')


@click.group(invoke_without_command=True)
@click.option('--color/--no-color', type=bool, default=True, help='Use colored output')
@click.argument('namelist1', required=True,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('namelist2', required=True,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def cli(color, namelist1, namelist2):
    """
    Compare two namelist files and print any differences.
    """
    if color:
        colors.enable()
    else:
        colors.disable()

    nml1 = f90nml.read(namelist1)
    nml2 = f90nml.read(namelist2)

    nml1 = sanitize_namelist(nml1)
    nml2 = sanitize_namelist(nml2)

    diff = namelist_diff(nml1, nml2)
    if diff:
        print_diff(diff)

if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
