"""Base class for dynamic pydantic models"""

import contextlib
import functools
import operator
import typing as ty
import warnings

import pydantic
import pydantic.fields
import pydantic_core

from .exceptions import AmbiguousDiscriminatorValueError, RegistrationError
from .union_mode import DiscriminatedConfig, UnionMode


def _inject_discriminator_field(
    cls: type[pydantic.BaseModel],
    disc_field: str,
    value: str,
) -> pydantic.fields.FieldInfo:
    """Injects the discriminator field into the given model

    Parameters
    ----------
    cls
        The BaseModel subclass
    disc_field
        Name of the discriminator field
    value
        Value of the discriminator field
    """
    cls.model_fields[disc_field] = pydantic.fields.FieldInfo(
        default=value,
        annotation=ty.Literal[value],  # type: ignore[not-a-type]
        frozen=True,
    )
    with contextlib.suppress(pydantic.errors.PydanticUndefinedAnnotation):
        cls.model_rebuild(force=True)
    return cls.model_fields[disc_field]


class TrackingGroup(pydantic.BaseModel):
    """Tracker for pydantic models"""

    name: str = pydantic.Field(
        description=(
            "Name of the tracking group. This is for human display, so it "
            "doesn't technically need to be globally unique, but it should be "
            "meaningfully named, as it will be used in error messages."
        ),
    )
    union_mode: UnionMode | None = pydantic.Field(
        None,
        description=(
            "Union validation strategy. Pass a DiscriminatedConfig instance "
            'or one of the plain strings "smart" or "left_to_right". You can '
            "also just pass the fields for DiscriminatedConfig to this "
            "model and they will be forwarded."
        ),
    )
    discriminator_field: str | None = pydantic.Field(
        None,
        description=(
            "Name of the discriminator field. NOTE: This field is "
            "here as an alias for union_mode.discriminator_field. Passing "
            "both a discriminator_field and a union_mode will result in an "
            "error."
        ),
    )
    discriminator_value_generator: ty.Callable[[type], str] | None = pydantic.Field(
        None,
        description=(
            "A callable that produces default values for the discriminator field"
        ),
    )
    plugin_entry_point: str | None = pydantic.Field(
        None,
        description=(
            "If given, then plugins packages will be supported through this "
            "Python entrypoint. The entrypoint can either be a function, "
            "which will be called, or simply a module, which will be "
            "imported. In either case, models found along the import path of "
            "the entrypoint will be registered. If the entrypoint is a "
            "function, additional models may be declared in the function."
        ),
    )
    models: dict[str, type[pydantic.BaseModel]] = pydantic.Field(
        {},
        description="The tracked models",
    )

    @pydantic.model_validator(mode="after")
    def _ensure_union_mode(self) -> "TrackingGroup":
        """There must be a union_mode

        This validator works as a guard on _coerce_union_mode to make
        """
        if self.union_mode is None:
            msg = (
                "union_mode is required. This normally indicates that you "
                "subclasses TrackingGroup and wrote an invalid validator, but "
                "could also be a bug with dynapydantic, so please file a bug "
                "report with a reproducer on how you got here if you suspect "
                "a bug."
            )
            raise ValueError(msg)

        # Ensure the top-level fields are in-sync
        if isinstance(self.union_mode, DiscriminatedConfig):
            self.discriminator_field = self.union_mode.discriminator_field
            self.discriminator_value_generator = (
                self.union_mode.discriminator_value_generator
            )
        else:
            self.discriminator_field = None
            self.discriminator_value_generator = None

        return self

    @pydantic.model_validator(mode="before")
    @classmethod
    def _coerce_union_mode(cls, data: ty.Any) -> ty.Any:  # noqa: ANN401
        """Coerce flat discriminator kwargs into a DiscriminatedConfig.

        Allows callers to pass ``discriminator_field`` and
        ``discriminator_value_generator`` at the top level and transparently
        assembles a ``DiscriminatedConfig`` from them. This avoids an extra
        import/nesting layer for the user.
        """
        if not isinstance(data, dict):
            return data

        disc_field = data.get("discriminator_field", None)
        has_disc_field = disc_field is not None
        union_mode = data.get("union_mode", None)
        has_union_mode = union_mode is not None

        if has_disc_field and has_union_mode:
            msg = (
                "Received both union_mode and discriminator_field; pass one "
                "or the other."
            )
            raise ValueError(msg)

        if has_disc_field and not has_union_mode:
            # Forward arguments to DiscriminatedConfig
            data["union_mode"] = {
                "discriminator_field": disc_field,
                "discriminator_value_generator": data.get(
                    "discriminator_value_generator",
                ),
            }
        elif not has_disc_field and not has_union_mode:
            msg = "Either union_mode or discriminator_field must be given"
            raise ValueError(msg)

        return data

    @property
    def _discriminated(self) -> DiscriminatedConfig | None:
        """Return the DiscriminatedMode config, or None if not discriminated."""
        return (
            self.union_mode
            if isinstance(self.union_mode, DiscriminatedConfig)
            else None
        )

    def load_plugins(self) -> None:
        """Load plugins to discover/register additional models"""
        if self.plugin_entry_point is None:
            return

        from importlib.metadata import entry_points  # noqa: PLC0415

        for ep in entry_points().select(group=self.plugin_entry_point):
            plugin = ep.load()
            if callable(plugin):
                plugin()

    def register(
        self,
        discriminator_value: str | None = None,
    ) -> ty.Callable[[type], type]:
        """Register a model into this group (decorator)

        Parameters
        ----------
        discriminator_value
            Value for the discriminator field. If not given, then
            discriminator_value_generator must be non-None or the
            discriminator field must be declared by hand.
        """

        def _wrapper(cls: type[pydantic.BaseModel]) -> type[pydantic.BaseModel]:
            if (dm := self._discriminated) is not None:
                disc = dm.discriminator_field
                field = cls.model_fields.get(disc)

                if field is None:
                    if discriminator_value is not None:
                        _inject_discriminator_field(cls, disc, discriminator_value)
                    elif dm.discriminator_value_generator is not None:
                        _inject_discriminator_field(
                            cls,
                            disc,
                            dm.discriminator_value_generator(cls),
                        )
                    else:
                        msg = (
                            f"unable to determine a discriminator value for "
                            f'{cls.__name__} in tracking group "{self.name}". '
                            "No value was passed to register(), "
                            "discriminator_value_generator was None and the "
                            f'"{disc}" field was not defined.'
                        )
                        raise RegistrationError(msg)
                elif (
                    discriminator_value is not None
                    and field.default != discriminator_value
                ):
                    msg = (
                        f"the discriminator value for {cls.__name__} was "
                        f'ambiguous, it was set to "{discriminator_value}" via '
                        f'register() and "{field.default}" via the '
                        f"discriminator field ({disc})."
                    )
                    raise AmbiguousDiscriminatorValueError(msg)

                self._register_with_discriminator_field(cls)
            else:
                if discriminator_value is not None:
                    warnings.warn(
                        f"discriminator_value={discriminator_value} was passed "
                        f'to register() but union_mode="{self.union_mode}" '
                        "does not use a discriminator. The value will be "
                        "ignored.",
                        stacklevel=2,
                    )
                self._register_plain(cls)
            return cls

        return _wrapper

    def register_model(self, cls: type[pydantic.BaseModel]) -> None:
        """Register the given model into this group

        Parameters
        ----------
        cls
            The model to register
        """
        if (dm := self._discriminated) is not None:
            disc = dm.discriminator_field
            if cls.model_fields.get(disc) is None:
                if dm.discriminator_value_generator is not None:
                    _inject_discriminator_field(
                        cls,
                        disc,
                        dm.discriminator_value_generator(cls),
                    )
                else:
                    msg = (
                        f"unable to determine a discriminator value for "
                        f'{cls.__name__} in tracking group "{self.name}", '
                        "discriminator_value_generator was None and the "
                        f'"{disc}" field was not defined.'
                    )
                    raise RegistrationError(msg)
            self._register_with_discriminator_field(cls)
        else:
            self._register_plain(cls)

    def union(
        self,
        *,
        plain: bool | None = None,
        annotated: bool | None = None,
    ) -> ty.Any:  # noqa: ANN401
        """Return the union of all registered models

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
        if annotated is not None:
            warnings.warn(
                "The `annotated` parameter is deprectated. Use `plain=True` to "
                "get a plain union. By default, behavior is governed by "
                "`union_mode`. Will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            plain = True if not annotated else plain

        union_mode = "smart" if plain else self.union_mode

        if isinstance(union_mode, DiscriminatedConfig):
            return ty.Annotated[
                functools.reduce(
                    operator.or_,
                    tuple(
                        ty.Annotated[x, pydantic.Tag(v)] for v, x in self.models.items()
                    ),
                ),
                pydantic.Field(discriminator=union_mode.discriminator_field),
            ]

        plain_union = functools.reduce(operator.or_, self.models.values())
        if union_mode == "left_to_right":
            return ty.Annotated[plain_union, pydantic.Field(union_mode="left_to_right")]

        # "smart" mode is pydantic's default behavior on a plain union
        return plain_union

    def _register_with_discriminator_field(self, cls: type[pydantic.BaseModel]) -> None:
        """Register the model with the default of the discriminator field

        Parameters
        ----------
        cls
            The class to register, must have the disciminator field set with a
            unique default value in the group.
        """
        disc = ty.cast("DiscriminatedConfig", self.union_mode).discriminator_field
        value = cls.model_fields[disc].default
        if value == pydantic_core.PydanticUndefined:
            msg = (
                f"{cls.__name__}.{disc} had no default value, it must "
                "have one which is unique among all tracked models."
            )
            raise RegistrationError(msg)

        if (other := self.models.get(value)) is not None and other is not cls:
            msg = (
                f'Cannot register {cls.__name__} under the "{value}" '
                f"identifier, which is already in use by {other.__name__}."
            )
            raise RegistrationError(msg)

        self.models[value] = cls

    def _register_plain(self, cls: type[pydantic.BaseModel]) -> None:
        """Register the model keyed by its class name.

        Used for smart / left_to_right modes where no discriminator field
        is involved.

        Parameters
        ----------
        cls
            The model to register.
        """
        key = str(id(cls))
        if (other := self.models.get(key)) is not None and other is not cls:
            msg = (
                f'Cannot register {cls.__name__} under the "{key}" '
                f"identifier, which is already in use by {other.__name__}."
            )
            raise RegistrationError(msg)
        self.models[key] = cls
