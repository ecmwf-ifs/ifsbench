# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Additional tools to support pydantic usage in ifsbench.
"""

from typing import Any
try:
    # Annotated is only available in typing for Python >=3.9.
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from pandas import DataFrame
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler

__all__ = ['PydanticDataFrame']

class _DataFrameAnnotation:
    """
    Annotation class for pandas.DataFrame. 

    This follows the example in https://docs.pydantic.dev/latest/concepts/types/#handling-third-party-types
    to add automatic serialisation/validation to support to pandas.DataFrame
    objects.
    """
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:

        def validate_from_dict(value: dict) -> DataFrame:
            """
            Validation function to support creating a pandas.DataFrame from
            a dictionary. The dictionary must have the same form as in the
            pandas.DataFrame.to_dict(orient='split') function.
            """
            result = DataFrame(**value)
            return result

        from_dict_schema = core_schema.chain_schema(
            [
                core_schema.dict_schema(),
                core_schema.no_info_plain_validator_function(validate_from_dict),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_dict_schema,
            python_schema=core_schema.union_schema(
                [
                    # Support creation/validation from other DataFrame objects
                    # and from dictionaries.
                    core_schema.is_instance_schema(DataFrame),
                    from_dict_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                # Serialise a frame. We have to use `orient=split` here, as
                # other orient-values may lead to a reordering of columns.
                lambda frame: frame.to_dict(orient='split')
            ),
        )

#: Annotated wrapper for DataFrame. This can be used to support
#: pandas.DataFrame objects in a pydantic class with automatic serialisation
#: and validation.
PydanticDataFrame = Annotated[DataFrame, _DataFrameAnnotation]
