# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod

__all__ = ['DataHandler']

class DataHandler(ABC):
    """
    Base class for data pipeline steps. Each DataHandler object describes one
    step in the data pipeline. Multiple DataHandler objects can be executed
    sequentially to perform specific data setup tasks.
    """


    @abstractmethod
    def execute(self, wdir, **kwargs):
        """
        Run this data handling operation in a given directory.

        Parameters
        ----------
        wdir    : str or :any:`pathlib.Path`
            The directory where the data handling should take place.
            Subclasses of DataHandler should operate relative to this path,
            unless absolute paths are given.
        """
        return NotImplemented

    # @abstractmethod
    # def to_dict(self):
    #     """
    #     Convert this object to a dictionary. It's class name and module name
    #     should be given as the "class" and "module" entry, respectively.
    #     """
    #     return NotImplemented

    # @classmethod
    # @abstractmethod
    # def from_dict(cls, data):
    #     """
    #     Convert a dictionary to an object of this type. This is the inverse
    #     function to "to_dict".
    #     """
    #     return NotImplemented
