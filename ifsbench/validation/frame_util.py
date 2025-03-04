# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

__all__ = ['get_float_columns', 'get_int_columns']

def get_float_columns(frame):
    """
    Extract a sub-dataframe which only holds columns that correspond to
    float values.

    Parameters
    ----------
    frame: pandas.DataFrame
        The dataframe that is processed.

    Returns
    -------
    pandas.DataFrame
        The sub-dataframe which holds only the float columns.
    """

    # Gather the column keys that correspond to float values.
    column_keys = []
    for key, value in frame.dtypes.items():
        if 'float' in str(value):
            column_keys.append(key)

    return frame[column_keys]

def get_int_columns(frame):
    """
    Extract a sub-dataframe which only holds columns that correspond to
    int values.

    Parameters
    ----------
    frame: pandas.DataFrame
        The dataframe that is processed.

    Returns
    -------
    pandas.DataFrame
        The sub-dataframe which holds only the int columns.
    """

    # Gather the column keys that correspond to int values.
    column_keys = []
    for key, value in frame.dtypes.items():
        if 'int' in str(value):
            column_keys.append(key)

    return frame[column_keys]
