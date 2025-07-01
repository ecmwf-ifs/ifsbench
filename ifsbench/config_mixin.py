# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Type, Union
from typing_extensions import Annotated, Literal

from pydantic import BaseModel, model_validator, TypeAdapter, Field, computed_field
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import ValidatorFunctionWrapHandler


from typing_extensions import Self, TypeAliasType

__all__ = ['AbstractDataClass', 'DataClass', 'CLASSNAME', 'RESERVED_NAMES']

# Reserved strings:
# CLASSNAME is used in the configuration to indicate which class has to be
# constructed with that configuration and cannot be used for member variables
# in implementing classes.
CLASSNAME = 'class_name'
RESERVED_NAMES = [
    CLASSNAME,
]


class DataClass(BaseModel, use_enum_values=True):
    """
    Base class for handling configurations in a format that can be used for storage.

    Uses pydantic for type checking and managing the config dictionary.
    """

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'DataClass':
        """Create instance based on config.

        Args:
            config: names and values for member variables.

        Returns:
            class instance
        """
        return cls(**config)

    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, List, None]]:
        """Get configuration for output.

        Args:
            with_class: Add/keep CLASSNAME key with class name to configuration.

        Returns:
            Configuration that can be used to create instance.
        """
        config = self.model_dump(exclude_none=True, round_trip=True)

        # Manually convert Path objects to str. In theorey, the subsequent
        # TypeAliasType thing should be able to do this but for some reason
        # this doesn't work.
        for k, v in config.items():
            if isinstance(v, Path):
                config[k] = str(v)

        # Add class name to the dictionary (or remove it if with_class==False).
        if with_class:
            config[CLASSNAME] = type(self).__name__
        else:
            config.pop(CLASSNAME, None)

        # Make sure that the output is indeed only dict/list/str/int/float/bool/None.
        # To do this, we use the pydantic validation. First, we define this recursive
        # data type.
        Allowed = TypeAliasType(
            'Allowed',
            'Union[Dict[Allowed, Allowed], List[Allowed], str, int, float, bool, None]',
        )

        allowed_type = TypeAdapter(Dict[str, Allowed])

        return allowed_type.validate_python(config)

class AbstractDataClass(DataClass):
    """
    Base class for DataClass hierarchies.

    This allows us to serialise dataclass hierarchies like
    ```
    class BaseClass(AbstractDataClass):
        ...

    class FirstClass(BaseClass):
        ...

    class SecondClass(BaseClass):
        ...


    class Accumulator(DataClass):
        objects: List[BaseClass]
    ```

    This is done by automatically adding ``CLASSNAME`` fields to each subclass
    and keeping track of the subclasses.
    """


    _subclasses: ClassVar[Dict[str, Type[Any]]] = {}
    _discriminating_type_adapter: ClassVar[TypeAdapter]

    @classmethod
    def _get_abstract_dataclass(cls) -> Type:
        """
        For a given class, return its parent class that inherits from
        AbstractDataClass.
        """
        candidates = [cls]

        while candidates:
            current = candidates.pop(0)

            if AbstractDataClass in current.__bases__:
                return current

            candidates += list(current.__bases__)

        return None

    @model_validator(mode='wrap')
    @classmethod
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> 'AbstractDataClass':
        """
        Recover the corresponding (sub-)class from data.
        """
        abstract_cls = cls._get_abstract_dataclass()

        if cls is abstract_cls:
            return abstract_cls._discriminating_type_adapter.validate_python(v)

        return handler(v)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        """
        When a new subclass is created, automatically add a CLASSNAME field
        and add it to the list of known subclasses.
        """

        # Add CLASSNAME field of type Literal[cls.__name__].
        cls.model_fields[CLASSNAME] = FieldInfo(
            annotation=Literal[cls.__name__],
            default=cls.__name__
        )

        # Force a model rebuild to apply the field changes.
        cls.model_rebuild(force=True)

        # Get the "root" AbstractDataClass and add the current class to the
        # list of subclasses.
        abstract_cls = cls._get_abstract_dataclass()

        if cls != abstract_cls:
            abstract_cls._subclasses[cls.__qualname__] = cls

            abstract_cls._discriminating_type_adapter = TypeAdapter(
                Annotated[
                    Union[tuple(abstract_cls._subclasses.values())],
                    Field(discriminator=CLASSNAME),
                ]
            )
