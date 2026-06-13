"""Base class for dynamic pydantic models"""

import dataclasses
import inspect
import typing as ty

import pydantic
from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema

from .exceptions import ConfigurationError, Error
from .tracking_group import TrackingGroup
from .union_mode import UnionRealization


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
    2. `union_realization`: When the union should be realized. See
           [`UnionRealization`][dynapydantic.UnionRealization] for more details
           on the various options. The default is to realize unions at model
           construction time.
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
        union_realization: str | UnionRealization | None = None,
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
            union_realization=union_realization,
            inherited=getattr(cls, "__DYNAPYDANTIC_STM_CONFIG__", None),
        )

        # If we are going to be tracked, walk the entire MRO (to support
        # multi-level tree) and register ourselves with each oe.
        if not cls.__DYNAPYDANTIC_STM_CONFIG__.exclude_from_union:
            for base in cls.__mro__:
                if (
                    issubclass(base, SubclassTrackingModel)
                    and base is not SubclassTrackingModel
                ):
                    base.__DYNAPYDANTIC__.register_model(cls)


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
    if isinstance(parent_tg := getattr(cls, "__DYNAPYDANTIC__", None), TrackingGroup):
        tg_kwargs = parent_tg.model_dump(
            exclude={
                "name",
                "models",
                "discriminator_field",
                "discriminator_value_generator",
            }
        )
        tg_kwargs |= kwargs
        if "discriminator_field" in kwargs:
            tg_kwargs.pop("union_mode", None)
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


@dataclasses.dataclass(frozen=True)
class _StmConfig:
    """Config for SubclassTrackingModel"""

    union_realization: UnionRealization
    exclude_from_union: bool

    @classmethod
    def create(
        cls,
        model_t: type[SubclassTrackingModel],
        *,
        exclude_from_union: bool | None,
        union_realization: str | UnionRealization | None = None,
        inherited: "_StmConfig | None" = None,
    ) -> "_StmConfig":
        """Create this model from the user's specified keyword arguments"""
        # Figure out the union realization time. Prefer direct argument, then
        # inherited value, then default of model construction time.
        if union_realization is None:
            union_realization = (
                inherited.union_realization
                if inherited is not None
                else UnionRealization.MODEL_CONSTRUCTION
            )
        elif not isinstance(union_realization, UnionRealization):
            try:
                union_realization = UnionRealization(union_realization)
            except (ValueError, TypeError) as e:
                msg = f"invalid union_realization: {e}"
                raise ConfigurationError(msg) from e

        # Figure out if model_t is are excluded from tracking unions. Prefer
        # direct argument, default to True if we are direct descendent of
        # SubclassTrackingModel and False otherwise. This is because direct
        # descendents tend to be the abstract base classes.
        if exclude_from_union is None:
            exclude_from_union = SubclassTrackingModel in model_t.__bases__

        return cls(
            union_realization=union_realization,
            exclude_from_union=exclude_from_union,
        )


_UNSET = object()


class ValidationTimeAdapter:
    """Pydantic type adapter for a dynapydantic-tracked field

    This adapter returns a validator that evaluates the union at validation time
    """

    @staticmethod
    def __get_pydantic_core_schema__(
        source_type: type[SubclassTrackingModel],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Get the pydantic schema for this type"""

        def _validate(value: ty.Any) -> ty.Any:  # noqa: ANN401
            try:
                adapter = source_type.__DYNAPYDANTIC__.type_adapter
            except Error as e:
                err_t = "dynapydantic_error"
                raise PydanticCustomError(err_t, "{e}", {"e": str(e)}) from e
            return adapter.validate_python(value)

        def _serialize(
            value: BaseModel,
            info: core_schema.SerializationInfo,
        ) -> dict[str, ty.Any]:
            newer_args = (
                "context",
                "exclude_computed_fields",
                "serialize_as_any",
                "polymorphic_serialization",
            )
            args: dict[str, ty.Any] = {}
            for arg in newer_args:
                if (v := getattr(info, arg, _UNSET)) is not _UNSET:
                    args[arg] = v

            return value.model_dump(
                mode=info.mode,
                # Pydantic's types don't match up
                include=info.include,  # type: ignore[bad-argument-type]
                exclude=info.exclude,  # type: ignore[bad-argument-type]
                by_alias=info.by_alias,
                exclude_unset=info.exclude_unset,
                exclude_defaults=info.exclude_defaults,
                exclude_none=info.exclude_none,
                round_trip=info.round_trip,
                warnings=False,
                **args,
            )

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
