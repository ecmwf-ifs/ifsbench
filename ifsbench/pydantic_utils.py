# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Additional tools to support pydantic usage in ifsbench.
"""

# Pylint complains about List and Union not used. They are in fact
# used and needed but the use is hidden in a string. See the
# serialise_frame function for more information.
# pylint: disable=W0611

from typing import Any, Dict, List, Union
from typing_extensions import TypeAliasType

try:
    # Annotated is only available in typing for Python >=3.9.
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated


from pandas import DataFrame, Timestamp
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler, AfterValidator, BeforeValidator, TypeAdapter

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

        def _str_to_timestamp_helper(value: str) -> Union[str, Timestamp]:
            """
            Helper function that takes a str and converts it to a
            pandas.Timestamp if it ends with _pd_timestamp. Otherwise it just
            returns the original string.
            """
            if value.endswith('_pd_timestamp'):
                return Timestamp(value.split('_pd_timestamp')[0])

            return value

        def validate_from_dict(value: dict) -> DataFrame:
            """
            Validation function to support creating a pandas.DataFrame from
            a dictionary. The dictionary must have the same form as in the
            pandas.DataFrame.to_dict(orient='split') function.
            """

            # Disable pylint "unused variable" warning here. TimestampType is
            # used, but that is hidden in a string. See the pydantic bug below.
            # pylint: disable=W0612

            # Custom type annotation that we will use to auto-convert
            # str objects that end with _pd_timestamp back to pandas.Timestamp
            # objects.
            TimestampType = Annotated[str, AfterValidator(_str_to_timestamp_helper)]

            # There is currently (pydantic 2.9.2) a bug which prevents us from just doing
            # the following (https://github.com/pydantic/pydantic/issues/11320):
            # Allowed = Union[Dict[str,'Allowed'], List['Allowed'], TimestampType, str, int, float, bool, None]
            #
            # Therefore, we use a TypeAlias workaround.

            Allowed = TypeAliasType(
                'Allowed',
                'Union[Dict[Allowed, Allowed], List[Allowed], TimestampType, str, int, float, bool, None]',
            )

            allowed_type = TypeAdapter(Dict[str, Allowed])

            frame_dict = allowed_type.validate_python(value)

            result = DataFrame.from_dict(frame_dict, orient='tight')
            return result

        def serialise_frame(value: DataFrame) -> Dict[str, Any]:
            """
            Serialise a DataFrame.
            """

            # Serialise a frame. We use `orient=tight` here, as this keeps the
            # column order intact when serialising.
            frame_dict = value.to_dict(orient='tight')

            # frame_dict is now a dictionary but may still contain data types
            # that can't easily be serialised (tuples, pandas.Timestamp and
            # probably some more).
            # We use some pydantic magic to autoconvert this to a dictionary of
            # dict, list, float, int, str, bool, None objects.

            # Disable pylint "unused variable" warning here. TimestampType is
            # used, but that is hidden in a string. See the pydantic bug below.
            # pylint: disable=W0612

            # Custom type annotation that we will use to auto-convert
            # pandas.Timestamp object to a string. We'll convert the timestamp
            # to its isoformat representation and add _pd_timestamp to it, so
            # we can convert it back to Timestamp object on validation.
            TimestampType = Annotated[
                str,
                BeforeValidator(
                    lambda x: x.isoformat() + '_pd_timestamp' if isinstance(x, Timestamp) else x
                ),
            ]

            # There is currently (pydantic 2.9.2) a bug which prevents us from just doing
            # the following (https://github.com/pydantic/pydantic/issues/11320):
            # Allowed = Union[Dict[str,'Allowed'], List['Allowed'], TimestampType, str, int, float, bool, None]
            #
            # Therefore, we use a TypeAlias workaround.

            Allowed = TypeAliasType(
                'Allowed',
                'Union[Dict[Allowed, Allowed], List[Allowed], TimestampType, str, int, float, bool, None]',
            )

            allowed_type = TypeAdapter(Dict[str, Allowed])

            frame_dict = allowed_type.validate_python(frame_dict)

            return frame_dict

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
            serialization=core_schema.plain_serializer_function_ser_schema(serialise_frame),
        )


#: Annotated wrapper for DataFrame. This can be used to support
#: pandas.DataFrame objects in a pydantic class with automatic serialisation
#: and validation.
PydanticDataFrame = Annotated[DataFrame, _DataFrameAnnotation]
