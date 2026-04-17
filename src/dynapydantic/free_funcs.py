"""Free function API for interacting with dynapydantic entities

We are using free functions to avoid cluttering the namespace of
SubclassTrackingModel, following pydantic's lead:
https://github.com/pydantic/pydantic/issues/10032
"""

import typing as ty

import pydantic

from .subclass_tracking_model import SubclassTrackingModel
from .tracking_group import TrackingGroup

ModelT = ty.TypeVar("ModelT", bound=SubclassTrackingModel)


def union(
    entity: TrackingGroup | type[SubclassTrackingModel], *, plain: bool | None = None
) -> ty.Any:  # noqa: ANN401 (type is determined at runtime)
    """Get the union of all tracked models in this entity

    Parameters
    ----------
    plain
        If set to `True`, a plain union of all members will be returned.
        Otherwise, the returned union will be annotated in accordance with
        the union mode.

    Returns
    -------
    Any
        If only 1 model is tracked, the model itself will be returned. If >1,
        model is tracked a union of all models will be returned. This union may
        be an `Annotated` union, depending on the `union_mode` of the entity and
        the value of `plain`.

    Raises
    ------
    NoRegisteredTypesError
        If no models are tracked by this entity.
    """
    if isinstance(entity, TrackingGroup):
        return entity.union(plain=plain)
    if isinstance(entity, type) and issubclass(entity, SubclassTrackingModel):
        return entity.__DYNAPYDANTIC__.union(plain=plain)

    msg = (
        "dynapydantic.union() works on TrackingGroup or "
        f"SubclassTrackingModel, was given {entity}, which was neither."
    )
    raise TypeError(msg)


def load_plugins(entity: TrackingGroup | type[SubclassTrackingModel]) -> None:
    """Load plugins to discover/register additional models"""
    if isinstance(entity, TrackingGroup):
        entity.load_plugins()
    elif isinstance(entity, type) and issubclass(entity, SubclassTrackingModel):
        entity.__DYNAPYDANTIC__.load_plugins()
    else:
        msg = (
            "dynapydantic.load_plugins() works on TrackingGroup or "
            f"SubclassTrackingModel, was given {entity}, which was neither."
        )
        raise TypeError(msg)


@ty.overload
def registered_models(entity: TrackingGroup) -> dict[str, type[pydantic.BaseModel]]: ...


@ty.overload
def registered_models(entity: type[ModelT]) -> dict[str, type[ModelT]]: ...


def registered_models(
    entity: TrackingGroup | type[ModelT],
) -> dict[str, type[pydantic.BaseModel]] | dict[str, type[ModelT]]:
    """Get the mapping of identifier -> model for all models tracked by the entity"""
    if isinstance(entity, TrackingGroup):
        return entity.models
    if isinstance(entity, type) and issubclass(entity, SubclassTrackingModel):
        return entity.__DYNAPYDANTIC__.models

    msg = (
        "dynapydantic.registered_models() works on TrackingGroup or "
        f"SubclassTrackingModel, was given {entity}, which was neither."
    )
    raise TypeError(msg)
