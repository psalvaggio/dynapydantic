"""Base class for dynamic pydantic models"""

import inspect
import typing as ty

import pydantic
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.errors import PydanticSchemaGenerationError
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import PydanticCustomError, core_schema

from .exceptions import ConfigurationError, Error
from .tracking_group import TrackingGroup


def direct_children_of_base_in_mro(derived: type, base: type) -> list[type]:
    """Find all classes in derived's MRO that are direct subclasses of base.

    Parameters
    ----------
    derived
        The class whose MRO is being examined.
    base
        The base class to find direct subclasses of.

    Returns
    -------
    Classes in derived's MRO that are direct subclasses of base.
    """
    return [cls for cls in derived.__mro__ if cls is not base and base in cls.__bases__]


class SubclassTrackingModel(pydantic.BaseModel):
    """Subclass-tracking BaseModel

    This will inject a [`TrackingGroup`][dynapydantic.TrackingGroup] into your
    class and automate the registration of subclasses.

    Inheriting from this class will augment your class with the following
    members functions:

    1. `registered_subclasses() -> dict[str, type[cls]]`:
        This will return a mapping of discriminator value to the corresponding
        subclass. See
        [`TrackingGroup.models`][dynapydantic.TrackingGroup.models] for details.
    2. `union() -> typing.Any`:
        This will return an (optionally) annotated subclass union. See
        [`TrackingGroup.union()`][dynapydantic.TrackingGroup.union] for details.
    3. `load_plugins() -> None`:
        If plugin_entry_point was specified, then this method will load plugin
        packages to discover additional subclasses. See
        [`TrackingGroup.load_plugins()`][dynapydantic.TrackingGroup.load_plugins]
        for more details.
    """

    def __init_subclass__(cls, *args, **kwargs) -> None:
        """Subclass hook"""
        # Intercept any kwargs that are intended for TrackingGroup or
        # __pydantic_init_subclass__
        sig = inspect.signature(SubclassTrackingModel.__pydantic_init_subclass__)
        super().__init_subclass__(
            *args,
            **{
                k: v
                for k, v in kwargs.items()
                if k not in TrackingGroup.model_fields and k not in sig.parameters
            },
        )

    # This method is too complex, here's the plan to simplify it:
    # We're polluting this models attributes by injecting and forwarding methods
    # from tracking group. As a result, we're limiting the possible field names
    # that these models can have. These should be free functions. We're going
    # to deprecate the methods to give people a release cycle to migrate off.
    # We should be able to remove the noqa after these are removed.
    @classmethod
    def __pydantic_init_subclass__(  # noqa: C901
        cls,
        *args,
        exclude_from_union: bool | None = None,
        implicit_polymorphic: bool | None = None,
        **kwargs,
    ) -> None:
        """Pydantic subclass hook"""
        if SubclassTrackingModel in cls.__bases__:
            # Intercept any kwargs that are intended for TrackingGroup
            super().__pydantic_init_subclass__(
                *args,
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k not in TrackingGroup.model_fields
                },
            )

            cls.__DYNAPYDANTIC_IMPLICIT_POLYMORPHIC__ = implicit_polymorphic

            if isinstance((tc := getattr(cls, "tracking_config", None)), TrackingGroup):
                cls.__DYNAPYDANTIC__ = tc
            else:
                try:
                    cls.__DYNAPYDANTIC__: TrackingGroup = TrackingGroup.model_validate(
                        {"name": f"{cls.__name__}-subclasses"} | kwargs,
                    )
                except pydantic.ValidationError as e:
                    msg = (
                        "SubclassTrackingModel subclasses must either have a "
                        "tracking_config: ClassVar[dynapydantic.TrackingGroup] "
                        "member or pass kwargs sufficient to construct a "
                        "dynapydantic.TrackingGroup in the class declaration. "
                        "The latter approach produced the following "
                        f"ValidationError:\n{e}"
                    )
                    raise ConfigurationError(msg) from e

            # Promote the tracking group's methods to the parent class
            if cls.__DYNAPYDANTIC__.plugin_entry_point is not None:

                def _load_plugins() -> None:
                    """Load plugins to register more models"""
                    cls.__DYNAPYDANTIC__.load_plugins()

                cls.load_plugins = staticmethod(_load_plugins)

            def _union(
                *,
                plain: bool | None = None,
                annotated: bool | None = None,
            ) -> ty.Any:  # noqa: ANN401 - return type is runtime-determined
                """Get the union of all tracked subclasses

                Parameters
                ----------
                plain
                    If set to `True`, a plain union of all members will be returned.
                    Otherwise, the returned union will be annotated in accordance with
                    the union mode.
                annotated
                    Deprecated. Use `plain=True` when you would have used
                    `annotated=False`.
                """
                # deprecation warning for annotated is in TrackingGroup
                return cls.__DYNAPYDANTIC__.union(plain=plain, annotated=annotated)

            cls.union = staticmethod(_union)

            def _subclasses() -> dict[str, type[pydantic.BaseModel]]:
                """Return a mapping of discriminator values to registered model"""
                return cls.__DYNAPYDANTIC__.models

            cls.registered_subclasses = staticmethod(_subclasses)

            if implicit_polymorphic:

                def _gpcs(
                    cls: type[SubclassTrackingModel],
                    source_type: type[pydantic.BaseModel],
                    handler: GetCoreSchemaHandler,
                    /,
                ) -> core_schema.CoreSchema:
                    if SubclassTrackingModel not in cls.__bases__:
                        return handler(source_type)

                    source_type = _assert_stm_subclass(source_type)

                    def _validate(value: ty.Any) -> ty.Any:  # noqa: ANN401
                        return _get_adapter(source_type).validate_python(value)

                    def _serialize(
                        value: pydantic.BaseModel,
                        info: core_schema.SerializationInfo,
                    ) -> dict[str, ty.Any]:
                        return value.model_dump(mode=info.mode)

                    return core_schema.no_info_plain_validator_function(
                        _validate,
                        serialization=core_schema.plain_serializer_function_ser_schema(
                            _serialize,
                            info_arg=True,
                            when_used="unless-none",
                            return_schema=core_schema.dict_schema(
                                core_schema.str_schema(), core_schema.any_schema()
                            ),
                        ),
                    )

                cls.__get_pydantic_core_schema__ = classmethod(_gpcs)  # type: ignore[bad-assignment]

                def _gpjs(
                    cls: type[SubclassTrackingModel],
                    core_schema: core_schema.CoreSchema,
                    handler: GetJsonSchemaHandler,
                ) -> JsonSchemaValue:
                    if SubclassTrackingModel not in cls.__bases__:
                        return handler(core_schema)
                    return handler(_get_adapter(cls).core_schema)

                cls.__get_pydantic_json_schema__ = classmethod(_gpjs)  # type: ignore[bad-assignment]

            return

        super().__pydantic_init_subclass__(*args, **kwargs)

        if exclude_from_union:
            return

        supers = direct_children_of_base_in_mro(cls, SubclassTrackingModel)
        for base in supers:
            base.__DYNAPYDANTIC__.register_model(cls)

    class PydanticAdaptor:
        """Pydantic type adaptor for SubclassTrackingModel"""

        @staticmethod
        def __get_pydantic_core_schema__(
            source_type: ty.Any,  # noqa: ANN401
            handler: GetCoreSchemaHandler,
        ) -> core_schema.CoreSchema:
            """Get the pydantic schema for this type"""
            source_type = _assert_stm_subclass(source_type)
            return handler(source_type.union())


def _assert_stm_subclass(
    t: ty.Any,  # noqa: ANN401
) -> type[SubclassTrackingModel]:
    if not isinstance(t, type) or not issubclass(
        t,
        SubclassTrackingModel,
    ):
        msg = (
            f"{t} was not a SubclassTrackingModel, "
            "so it is incompatible with dynapydantic.Polymorphic"
        )
        raise PydanticSchemaGenerationError(msg)
    return t


def _get_adapter(
    source_type: type[SubclassTrackingModel],
) -> pydantic.TypeAdapter:
    try:
        return source_type.__DYNAPYDANTIC__.type_adapter
    except Error as e:
        err_t = "dynapydantic_error"
        raise PydanticCustomError(err_t, "{e}", {"e": str(e)}) from e
