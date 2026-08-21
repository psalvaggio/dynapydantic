"""Base class for dynamic pydantic models"""

import dataclasses
import functools
import inspect
import json
import typing as ty

import pydantic
from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    PydanticInvalidForJsonSchema,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import PydanticCustomError, core_schema

from .exceptions import ConfigurationError, Error
from .tracking_group import TrackingGroup
from .union_mode import UnionRealization
from .version_check import pydantic_ge


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
        # multi-level tree) and register ourselves with each one.
        if not cls.__DYNAPYDANTIC_STM_CONFIG__.exclude_from_union:
            for base in cls.__mro__:
                if (
                    issubclass(base, SubclassTrackingModel)
                    and base is not SubclassTrackingModel
                    and not _is_uninstantiated_generic(base)
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

        if exclude_from_union is None:
            exclude_from_union = _exclude_from_union_default(model_t)

        return cls(
            union_realization=union_realization,
            exclude_from_union=exclude_from_union,
        )


def _exclude_from_union_default(model_t: type[SubclassTrackingModel]) -> bool:
    """Determine the default value for exclude_from_union"""
    # In general, this shall default to False. It will default to True if:
    # 1. We are direct descendent of SubclassTrackingModel. This is
    #    because direct descendents tend to be the abstract base classes.
    if SubclassTrackingModel in model_t.__bases__:
        return True

    # 2. We are a generic class with a TypeVar argument (non-concrete).
    if _is_uninstantiated_generic(model_t):
        return True

    # 3. We are a concrete generic class and our origin is a direct
    #    descendent of SubclassTrackingModel. Combined case of 1 and 2. A
    #    concrete generic that is not a direct descendent is the same as any
    #    other class in the middle of an inheritance tree.
    generic_origin = model_t.__pydantic_generic_metadata__["origin"]
    if generic_origin is None:
        return False
    return SubclassTrackingModel in generic_origin.__bases__


def _is_uninstantiated_generic(model_t: type[SubclassTrackingModel]) -> bool:
    """Determine if this a generic model with uninstantiated args"""
    generic_args = model_t.__pydantic_generic_metadata__["parameters"]
    return any(isinstance(arg, ty.TypeVar) for arg in generic_args)


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

        def _validate(
            value: ty.Any,  # noqa: ANN401
            info: core_schema.ValidationInfo,
            *,
            strict: bool,
        ) -> ty.Any:  # noqa: ANN401
            try:
                adapter = source_type.__DYNAPYDANTIC__.type_adapter
            except Error as e:
                err_t = "dynapydantic_error"
                raise PydanticCustomError(err_t, "{e}", {"e": str(e)}) from e

            kwargs = _validation_kwargs(info)
            kwargs["strict"] = strict
            if info.mode == "json":
                # Field validators receive JSON after the enclosing document has
                # already been decoded. Re-encode the field so the nested
                # adapter can apply JSON-specific strict-validation behavior.
                # https://github.com/pydantic/pydantic/issues/11154
                kwargs.pop("from_attributes", None)
                try:
                    value_j = json.dumps(value)
                # Since the object came from a JSON load, this shouldn't ever
                # occur, but just being overly defensive.
                except (TypeError, ValueError, OverflowError) as e:
                    err_t = "json_reencode_failure"
                    msg = "JSON re-encoding failed: {e}"
                    raise PydanticCustomError(err_t, msg, {"e": str(e)}) from e

                return adapter.validate_json(value_j, **kwargs)
            return adapter.validate_python(value, **kwargs)

        def _serialize(
            value: BaseModel,
            info: core_schema.SerializationInfo,
        ) -> dict[str, ty.Any]:
            # These arguments we're going to attempt but not require
            soft_args = (
                # These were added after 2.0 (we pin >= 2)
                "context",
                "exclude_computed_fields",
                "serialize_as_any",
                "polymorphic_serialization",
            )
            args: dict[str, ty.Any] = {
                # SerializationInfo doesn't expose warnings, so we have to
                # pick one option
                "warnings": False,
            }
            for arg in soft_args:
                if (v := getattr(info, arg, _UNSET)) is not _UNSET:
                    args[arg] = v

            return value.model_dump(
                mode=info.mode,
                # Pydantic's types on SerializationInfo's include/exclude don't
                # match up with the corresponding parameter types on model_dump
                include=info.include,  # type: ignore[bad-argument-type]
                exclude=info.exclude,  # type: ignore[bad-argument-type]
                by_alias=info.by_alias,
                exclude_unset=info.exclude_unset,
                exclude_defaults=info.exclude_defaults,
                exclude_none=info.exclude_none,
                round_trip=info.round_trip,
                **args,
            )

        _validate_lax = functools.partial(_validate, strict=False)
        _validate_strict = functools.partial(_validate, strict=True)

        serialization = core_schema.plain_serializer_function_ser_schema(
            _serialize,
            info_arg=True,
            when_used="unless-none",
            return_schema=core_schema.dict_schema(
                core_schema.str_schema(), core_schema.any_schema()
            ),
        )
        metadata = {"dynapydantic_source_type": source_type}
        return core_schema.lax_or_strict_schema(
            core_schema.with_info_plain_validator_function(_validate_lax),
            core_schema.with_info_plain_validator_function(_validate_strict),
            metadata=metadata,
            serialization=serialization,
        )

    @staticmethod
    def __get_pydantic_json_schema__(
        schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Lazily build the JSON schema from the currently registered subclasses

        Runs whenever JSON schema generation actually happens (e.g. a call to
        `model_json_schema()`), not when the core schema was first built.
        Reflects whatever subclasses are registered with the `TrackingGroup`
        at the time of the call.

        Parameters
        ----------
        schema
            Schema for the field type
        handler
            JSON schema handler to convert core_schemas to JSON schemas

        Returns
        -------
        JsonSchemaValue
            JSON schema for the field

        Raises
        ------
        pydantic.errors.PydanticInvalidForJsonSchema
            If the JSON schema was unable to be generated.
        """
        try:
            source_type = schema["metadata"]["dynapydantic_source_type"]
        except KeyError as e:
            msg = "Missing dynapydantic schema metadata."
            raise PydanticInvalidForJsonSchema(msg) from e

        try:
            union_schema = source_type.__DYNAPYDANTIC__.type_adapter.core_schema
        except Error as e:
            msg = str(e)
            raise PydanticInvalidForJsonSchema(msg) from e

        return handler(union_schema)


def _validation_kwargs(
    info: core_schema.ValidationInfo,
) -> dict[str, ty.Any]:
    """Extract keyword arguments for TypeAdapter.validate_python from info."""
    kwargs: dict[str, ty.Any] = {}

    if (ctx := getattr(info, "context", None)) is not None:
        kwargs["context"] = ctx

    if (config := getattr(info, "config", None)) is not None:
        # .validate() didn't support extra until 2.12
        if (
            pydantic_ge((2, 12, 0))
            and (val := config.get("extra_fields_behavior")) is not None
        ):
            kwargs["extra"] = val

        if pydantic_ge((2, 11, 0)):
            if (val := config.get("validate_by_alias")) is not None:
                kwargs["by_alias"] = val
            if (val := config.get("validate_by_name")) is not None:
                kwargs["by_name"] = val

        if (val := config.get("from_attributes")) is not None:
            kwargs["from_attributes"] = val

    return kwargs
