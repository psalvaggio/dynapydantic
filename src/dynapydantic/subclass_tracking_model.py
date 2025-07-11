"""Base class for dynamic pydantic models"""

import typing as ty

import pydantic

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
    """Subclass-tracking BaseModel"""

    def __init_subclass__(
        cls,
        *args,
        exclude_from_union: bool | None = None,
        **kwargs,
    ) -> None:
        """Subclass hook"""
        # Intercept any kwargs that are intended for TrackingGroup
        super().__pydantic_init_subclass__(
            *args,
            **{k: v for k, v in kwargs.items() if k not in TrackingGroup.model_fields},
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

            if isinstance(getattr(cls, "tracking_config", None), TrackingGroup):
                cls.__DYNAPYDANTIC__ = cls.tracking_config
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

            def _union(*, annotated: bool = True) -> ty.GenericAlias:
                """Get the union of all tracked subclasses

                Parameters
                ----------
                annotated
                    Whether this should be an annotated union for usage as a
                    pydantic field annotation, or a plain typing.Union for a
                    regular type annotation.
                """
                return cls.__DYNAPYDANTIC__.union(annotated=annotated)

            cls.union = staticmethod(_union)

            def _subclasses() -> dict[str, type[cls]]:
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
