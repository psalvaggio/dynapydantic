"""Base class for dynamic pydantic models"""

import inspect
import typing as ty

import pydantic
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
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

    Similar to `BaseModel`, `SubclassTrackingModel` can take arguments in the
    class declaration. Arguments from `BaseModel` will be forwarded.
    Additionally, any fields from `TrackingGroup` will be forwarded to the
    internal `TrackingGroup` instance. The following additional arguments are
    supported:

    1. `exclude_from_union`: This flag is intended to be used with descendents
           of `SubclassTrackingModel`. If `True`, this subclass will be omitted
           from tracking.
    2. `implicit_polymorphic`: This flag is intended to be used with direct
           descendents of `SubclassTrackingModel`. If `True`, then the core
           schema of this class will be overridden. This allows polymorphic
           parsing to occur without the use of
           [`Polymorphic`][dynapydantic.Polymorphic]. In addition, it is not
           necessary to call `model_rebuild` on recursive models. This feature
           is currently **EXPERIMENTAL** and does incur a runtime penalty.
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

    @classmethod
    def __pydantic_init_subclass__(
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

            cls.__DYNAPYDANTIC_IMPLICIT_POLYMORPHIC__: ty.ClassVar[bool] = (
                implicit_polymorphic if implicit_polymorphic is not None else False
            )

            if isinstance((tc := getattr(cls, "tracking_config", None)), TrackingGroup):
                cls.__DYNAPYDANTIC__: ty.ClassVar[TrackingGroup] = tc
            else:
                try:
                    cls.__DYNAPYDANTIC__: ty.ClassVar[TrackingGroup] = (
                        TrackingGroup.model_validate(
                            {"name": f"{cls.__name__}-subclasses"} | kwargs,
                        )
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

            # If we're an implicit polymorphic model, we need to override our
            # pydantic schema.
            if implicit_polymorphic:
                cls.__get_pydantic_core_schema__ = classmethod(  # type: ignore[bad-assignment]
                    _get_pydantic_core_schema
                )

                cls.__get_pydantic_json_schema__ = classmethod(  # type: ignore[bad-assignment]
                    _get_pydantic_json_schema
                )

            return

        super().__pydantic_init_subclass__(*args, **kwargs)

        if exclude_from_union:
            return

        supers = direct_children_of_base_in_mro(cls, SubclassTrackingModel)
        for base in supers:
            base.__DYNAPYDANTIC__.register_model(cls)


def _get_adapter(
    source_type: type[SubclassTrackingModel],
) -> pydantic.TypeAdapter:
    try:
        return source_type.__DYNAPYDANTIC__.type_adapter
    except Error as e:
        err_t = "dynapydantic_error"
        raise PydanticCustomError(err_t, "{e}", {"e": str(e)}) from e


def _get_pydantic_core_schema(
    cls: type[SubclassTrackingModel],
    source_type: type[pydantic.BaseModel],
    handler: GetCoreSchemaHandler,
    /,
) -> core_schema.CoreSchema:
    """Get the pydantic core schema for this type"""
    if SubclassTrackingModel not in cls.__bases__:
        return handler(source_type)

    def _validate(value: ty.Any) -> ty.Any:  # noqa: ANN401
        return _get_adapter(
            ty.cast("type[SubclassTrackingModel]", source_type)
        ).validate_python(value)

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


def _get_pydantic_json_schema(
    cls: type[SubclassTrackingModel],
    cs: core_schema.CoreSchema,
    handler: GetJsonSchemaHandler,
    /,
) -> JsonSchemaValue:
    """Get the pydantic JSON schema for this type"""
    if SubclassTrackingModel in cls.__bases__:
        return handler(_get_adapter(cls).core_schema)
    return handler(cs)
