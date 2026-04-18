"""Base class for dynamic pydantic models"""

import dataclasses
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
           from tracking. The default for this flag is `True` for direct
           descendents of `SubclassTrackingModel` and `False` otherwise.
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
        # Forward along any unexpected arguments that were not intended
        # for TrackingGroup.
        super().__pydantic_init_subclass__(
            *args,
            **{k: v for k, v in kwargs.items() if k not in TrackingGroup.model_fields},
        )

        # Initialize the tracking group
        cls.__DYNAPYDANTIC__: ty.ClassVar[TrackingGroup] = _init_tracking_group(
            cls, **kwargs
        )

        # Initialize our SubclassTrackingModel-specific config
        cls.__DYNAPYDANTIC_STM_CONFIG__: ty.ClassVar[_StmConfig] = _StmConfig.create(
            cls,
            exclude_from_union=exclude_from_union,
            implicit_polymorphic=implicit_polymorphic,
            inherited=getattr(cls, "__DYNAPYDANTIC_STM_CONFIG__", None),
        )

        # If we're an implicit polymorphic model, we need to override our
        # pydantic schema.
        if cls.__DYNAPYDANTIC_STM_CONFIG__.implicit_polymorphic:
            cls.__get_pydantic_core_schema__ = classmethod(  # type: ignore[bad-assignment]
                _get_pydantic_core_schema
            )
            cls.__get_pydantic_json_schema__ = classmethod(  # type: ignore[bad-assignment]
                _get_pydantic_json_schema
            )

        if not cls.__DYNAPYDANTIC_STM_CONFIG__.exclude_from_union:
            for base in cls.__mro__:
                if (
                    tg := getattr(base, "__DYNAPYDANTIC__", None)
                ) is not None and isinstance(tg, TrackingGroup):
                    tg.register_model(cls)


def _init_tracking_group(
    cls: type[SubclassTrackingModel],
    **kwargs,
) -> TrackingGroup:
    """Initialize the tracking model embedded in this model"""
    # If the user already defined one, use it
    if isinstance((tc := getattr(cls, "tracking_config", None)), TrackingGroup):
        return tc

    # Otherwise, we need to make it. We can inherit arguments from our
    # parent class(es) if they have TrackingGroup's and then allow any
    # kwargs directly passed here to override.
    if (parent_tg := getattr(cls, "__DYNAPYDANTIC__", None)) is not None:
        tg_kwargs = parent_tg.model_dump(exclude={"name", "models"}) | kwargs
    else:
        tg_kwargs = kwargs
    tg_kwargs.setdefault("name", f"{cls.__name__}-subclasses")

    try:
        return TrackingGroup(**tg_kwargs)
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


@dataclasses.dataclass
class _StmConfig:
    """Config for SubclassTrackingModel"""

    implicit_polymorphic: bool
    exclude_from_union: bool

    @classmethod
    def create(
        cls,
        model_t: type[SubclassTrackingModel],
        *,
        exclude_from_union: bool | None,
        implicit_polymorphic: bool | None,
        inherited: ty.Self | None,
    ) -> ty.Self:
        # Figure out if we are an implicit polymorphic model. Prefer direct
        # argument, then inherited, then default False.
        if implicit_polymorphic is None:
            implicit_polymorphic = (
                inherited.implicit_polymorphic if inherited is not None else False
            )

        # Figure out if model_t is are excluded from tracking unions. Prefer
        # direct argument, default to True if we are direct descendent of
        # SubclassTrackingModel and False otherwise.
        if exclude_from_union is None:
            exclude_from_union = SubclassTrackingModel in model_t.__bases__

        return cls(
            implicit_polymorphic=implicit_polymorphic,
            exclude_from_union=exclude_from_union,
        )


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
