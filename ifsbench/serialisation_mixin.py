# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Type, Union
from typing_extensions import Annotated, Literal, TypeAliasType

from pydantic import BaseModel, Field, model_validator, TypeAdapter, model_serializer
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import (
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidatorFunctionWrapHandler,
)


__all__ = [
    "SubclassableSerialisationMixin",
    "SerialisationMixin",
    "CLASSNAME",
    "RESERVED_NAMES",
]

# Reserved strings:
# CLASSNAME is used in the configuration to indicate which class has to be
# constructed with that configuration and cannot be used for member variables
# in implementing classes.
CLASSNAME = "class_name"
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
    ) -> "SerialisationMixin":
        """Create instance based on config.

        Args:
            config: names and values for member variables.

        Returns:
            class instance
        """
        adapter = TypeAdapter(cls)
        return adapter.validate_python(config)

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
            "Allowed",
            "Union[Dict[Allowed, Allowed], List[Allowed], str, int, float, bool, None]",
        )

        allowed_type = TypeAdapter(Dict[str, Allowed])

        return allowed_type.validate_python(config)

    # Pylint complains that this is overriding the pydantic copy function. As
    # the pydantic copy function is deprecated (and might get removed in the
    # future) we define our own copy version here.
    # pylint: disable=W0221
    def copy(self, deep: bool = False) -> "SerialisationMixin":
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

    @model_serializer(mode="wrap")
    def _serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Any:
        """
        Workaround for proper serialisation of subclasses.

        When pydantic tries to serialise something of type BaseClass, it will
        use the serialisation method of BaseClass, even if the object is an
        instance of a child class. This is not desired here, therefore we use
        this serializer to always use the serialisation function of the actual
        object.
        """

        # Essentially we call the model_dump function of the actual object
        # (self). As the model_dump function eventually invokes this function
        # again, we have to make sure that we are not stuck in an endless
        # recursion.
        # To avoid this, we register if we started a recursion for this object,
        # using the info.context object.

        if isinstance(info.context, dict):
            context = dict(info.context)
        else:
            context = {}

        if "recursive" not in context:
            context["recursive"] = {}

        # We use the ID of self to detect if we've called this recursively or not.
        me = id(self)

        # Check if we are in a recursive call to this function. If we are, just
        # use the default serialisation handler (which this function wraps) to
        # do the serialisation.
        recursive = context["recursive"].get(me, False)

        if recursive:
            # We exit the recursion here by calling the handler directly. Delete
            # the recursive flag here, otherwise this may cause issues later.
            del context["recursive"][me]
            return handler(self)

        context["recursive"][me] = True

        # Convert options into a dictionary so we can pass it to model_dump.
        # Unfortunately, the info object has no routine for this inbuilt and
        # the parameters that it holds also vary depending on the
        # Python/pydantic version. Therefore we have to check which attributes
        # exist.
        options = {}

        for key in [
            "mode",
            "by_alias",
            "exclude_unset",
            "exclude_defaults",
            "exclude_none",
            "exclude_computed_fields",
            "round_trip",
            "serialize_as_any",
        ]:
            if hasattr(info, key):
                options[key] = getattr(info, key)

        # Call model_dump, using the actual self object and all the options
        # that are stored in info.
        return self.model_dump(**options, context=context)

    @model_validator(mode="wrap")
    @classmethod
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> "SubclassableSerialisationMixin":
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
            annotation=Literal[cls.__name__], default=cls.__name__
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
