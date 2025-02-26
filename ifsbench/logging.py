# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Logging levels and functionality
"""

import logging
import sys


__all__ = ['debug', 'header', 'info', 'warning', 'success', 'error',
	   'logger', 'colors', 'DEBUG', 'INFO', 'WARNING', 'ERROR']


class colors:
    """
    Color definitions for logging

    This provides a number of different color definitions to use for
    logging output. They are intended to be used as a formatting string
    as, for example:

    .. code-block::

       colored_message = colors.WARNING % msg

    Attributes
    ----------
    HEADER : str
        Highlight color for important "headline"-type messages
    OKBLUE : str
        Blue highlight color for confirmation-type messages
    OKGREEN : str
        Green highlight color for confirmation-type messages
    WARNING : str
        Highlight color for warnings
    FAIL : str
        Highlight color for errors
    BOLD : str
        Emphasised format with a bold font weight
    UNDERLINE : str
        Emphasised format with an underlined font
    """

    @staticmethod
    def enable():
        """
        Enable color formatting
        """
        colors.HEADER = '\033[95m%s\033[0m'
        colors.OKBLUE = '\033[94m%s\033[0m'
        colors.OKGREEN = '\033[92m%s\033[0m'
        colors.WARNING = '\033[93m%s\033[0m'
        colors.FAIL = '\033[91m%s\033[0m'
        colors.BOLD = '\033[1m%s\033[0m'
        colors.UNDERLINE = '\033[4m%s\033[0m'

    @staticmethod
    def disable():
        """
        Disable color formatting
        """
        colors.HEADER = '%s'
        colors.OKBLUE = '%s'
        colors.OKGREEN = '%s'
        colors.WARNING = '%s'
        colors.FAIL = '%s'
        colors.BOLD = '%s'
        colors.UNDERLINE = '%s'


# Set colours on true terminals
if sys.stdout.isatty():
    colors.enable()
else:
    colors.disable()


logger = logging.getLogger('ecbundle')
_ch = logging.StreamHandler()
logger.addHandler(_ch)
logger.setLevel(logging.INFO)

INFO = logging.INFO
DEBUG = logging.DEBUG
WARNING = logging.WARNING
ERROR = logging.ERROR

def debug(msg, *args, **kwargs):
    msg = colors.OKBLUE % msg
    logger.log(logging.DEBUG, msg, *args, **kwargs)


def header(msg, *args, **kwargs):
    msg = colors.HEADER % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    msg = colors.OKBLUE % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def success(msg, *args, **kwargs):
    msg = colors.OKGREEN % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    msg = colors.WARNING % msg
    logger.log(logging.WARNING, msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    msg = colors.FAIL % msg
    logger.log(logging.ERROR, msg, *args, **kwargs)
