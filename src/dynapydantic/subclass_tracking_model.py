"""Base class for dynamic pydantic models"""

import inspect
import typing as ty

import pydantic
from pydantic import GetCoreSchemaHandler
from pydantic.errors import PydanticSchemaGenerationError
from pydantic_core import core_schema

from .exceptions import ConfigurationError
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

    @classmethod
    def __pydantic_init_subclass__(
        cls,
        *args,
        exclude_from_union: bool | None = None,
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
            if not isinstance(source_type, type) or not issubclass(
                source_type,
                SubclassTrackingModel,
            ):
                msg = (
                    f"{source_type} was not a SubclassTrackingModel, "
                    "so it is incompatible with dynapydantic.Polymorphic"
                )
                raise PydanticSchemaGenerationError(msg)
            return handler(source_type.union())
