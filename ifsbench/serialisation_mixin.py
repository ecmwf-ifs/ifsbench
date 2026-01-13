# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Type, Union
from typing_extensions import Annotated, Literal, TypeAliasType

from pydantic import BaseModel, Field, model_validator, TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import ValidatorFunctionWrapHandler


__all__ = ['SubclassableSerialisationMixin', 'SerialisationMixin', 'CLASSNAME', 'RESERVED_NAMES']

# Reserved strings:
# CLASSNAME is used in the configuration to indicate which class has to be
# constructed with that configuration and cannot be used for member variables
# in implementing classes.
CLASSNAME = 'class_name'
RESERVED_NAMES = [
    CLASSNAME,
]


class SerialisationMixin(BaseModel, use_enum_values=True, validate_assignment=True):
    """
    Mixin class that enables automatic serialisation features for this class.

    This class uses the ``pydantic`` module to enable automatic serialisation of
    an objects' attributes.
    All attributes must be defined with typehints.
    """

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'SerialisationMixin':
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

    # Pylint complains that this is overriding the pydantic copy function. As
    # the pydantic copy function is deprecated (and might get removed in the
    # future) we define our own copy version here.
    # pylint: disable=W0221
    def copy(self, deep: bool=False) -> 'SerialisationMixin':
        """
        Create a copy of this object.

        Args:
            deep: If True, create a deep copy.
        """

        return self.model_copy(deep=deep)

class SubclassableSerialisationMixin(SerialisationMixin):
    """
    Mixin class that enables automatic serialisation features for subclasses.

    This allows us to serialise dataclass hierarchies like
    ```
    class BaseClass(SubclassableSerialisationMixin):
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
        For a given class, return the first parent class that inherits from
        SubclassableSerialisationMixin.
        """
        candidates = [cls]

        # Do a breadth-first search over the parent classes.
        while candidates:
            current = candidates.pop(0)

            if SubclassableSerialisationMixin in current.__bases__:
                return current

            candidates += list(current.__bases__)

        return None

    @model_validator(mode='wrap')
    @classmethod
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> 'SubclassableSerialisationMixin':
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

        # Get the "root" SubclassableSerialisationMixin and add the current class to the
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
