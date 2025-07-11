"""Base class for dynamic pydantic models"""

import typing as ty

import pydantic
import pydantic.fields
import pydantic_core

from .exceptions import AmbiguousDiscriminatorValueError, RegistrationError


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
        annotation=ty.Literal[value],
        frozen=True,
    )
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
    discriminator_field: str = pydantic.Field(
        description="Name of the discriminator field",
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
    discriminator_value_generator: ty.Callable[[type], str] | None = pydantic.Field(
        None,
        description=(
            "A callable that produces default values for the discriminator field"
        ),
    )
    models: dict[str, type[pydantic.BaseModel]] = pydantic.Field(
        {},
        description="The tracked models",
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

        def _wrapper(cls: type[pydantic.BaseModel]) -> None:
            disc = self.discriminator_field
            field = cls.model_fields.get(self.discriminator_field)
            if field is None:
                if discriminator_value is not None:
                    _inject_discriminator_field(cls, disc, discriminator_value)
                elif self.discriminator_value_generator is not None:
                    _inject_discriminator_field(
                        cls,
                        disc,
                        self.discriminator_value_generator(cls),
                    )
                else:
                    msg = (
                        f"unable to determine a discriminator value for "
                        f'{cls.__name__} in tracking group "{self.name}". No '
                        "value was passed to register(), "
                        "discriminator_value_generator was None and the "
                        f'"{disc}" field was not defined.'
                    )
                    raise RegistrationError(msg)
            elif (
                discriminator_value is not None and field.default != discriminator_value
            ):
                msg = (
                    f"the discriminator value for {cls.__name__} was "
                    f'ambiguous, it was set to "{discriminator_value}" via '
                    f'register() and "{field.default}" via the discriminator '
                    f"field ({self.discriminator_field})."
                )
                raise AmbiguousDiscriminatorValueError(msg)

            self._register_with_discriminator_field(cls)
            return cls

        return _wrapper

    def register_model(self, cls: type[pydantic.BaseModel]) -> None:
        """Register the given model into this group

        Parameters
        ----------
        cls
            The model to register
        """
        disc = self.discriminator_field
        if cls.model_fields.get(self.discriminator_field) is None:
            if self.discriminator_value_generator is not None:
                _inject_discriminator_field(
                    cls,
                    disc,
                    self.discriminator_value_generator(cls),
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

    def _register_with_discriminator_field(self, cls: type[pydantic.BaseModel]) -> None:
        """Register the model with the default of the discriminator field

        Parameters
        ----------
        cls
            The class to register, must have the disciminator field set with a
            unique default value in the group.
        """
        disc = self.discriminator_field
        field = cls.model_fields.get(disc)
        value = field.default
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

    def union(self, *, annotated: bool = True) -> ty.GenericAlias:
        """Return the union of all registered models"""
        return (
            ty.Annotated[
                ty.Union[  # noqa: UP007
                    tuple(
                        ty.Annotated[x, pydantic.Tag(v)] for v, x in self.models.items()
                    )
                ],
                pydantic.Field(discriminator=self.discriminator_field),
            ]
            if annotated
            else ty.Union[tuple(self.models.values())]  # noqa: UP007
        )
