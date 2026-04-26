"""Custom annotations for dynapydantic"""

import typing as ty

from pydantic import GetCoreSchemaHandler, PydanticSchemaGenerationError
from pydantic_core import core_schema

from .free_funcs import union
from .subclass_tracking_model import (
    SubclassTrackingModel,
    ValidationTimeAdapter,
)
from .tracking_group import TrackingGroup
from .union_mode import UnionRealization

ModelT = ty.TypeVar("ModelT", bound=SubclassTrackingModel)


class ModelConstructionTimeAdapter:
    """Pydantic type adapter for SubclassTrackingModel"""

    @staticmethod
    def __get_pydantic_core_schema__(
        source_type: type[SubclassTrackingModel],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Get the pydantic schema for this type"""
        return handler(union(source_type))


class Polymorphic:
    """Annotation used to mark a type as having duck-typing behavior

    This annotation is only valid for SubclassTrackingModel's.

    Similar to SerializeAsAny, a field annotated with this shall serialize as
    according to its actual type, not the field annotation type. In addition,
    parsing will function as if the field annotation type were the union of
    all tracked subclasses.

    If a UnionRealization (or the string value of one) is passed as the
    second argument, it will override the default value for the union
    realization that is stored in the class.
    """

    def __class_getitem__(
        cls,
        item: type[ModelT] | tuple[type[ModelT], UnionRealization | str],
    ) -> ty.Annotated[type[ModelT], ...]:
        """Get the annotation for the pydantic field"""
        if isinstance(item, tuple):
            if len(item) > 2:  # noqa: PLR2004
                msg = (
                    "dynapydantic.Polymorphic takes 1 or 2 arguments "
                    f"({len(item)} given)"
                )
                raise TypeError(msg)

            return _polymorphic_cgi(*item)
        return _polymorphic_cgi(item)


def _polymorphic_cgi(
    cls: type[ModelT],
    union_realization: UnionRealization | str | None = None,
) -> ty.Annotated[type[ModelT], ...]:
    if not isinstance(cls, type):
        msg = f"dynapydantic.Polymorphic must be given a type, not {cls}"
        raise TypeError(msg)

    if not issubclass(cls, SubclassTrackingModel):
        msg = f"Polymorphic was given {cls}, which was not a SubclassTrackingModel."
        raise PydanticSchemaGenerationError(msg)

    cfg = cls.__DYNAPYDANTIC_STM_CONFIG__
    union_realization = (
        UnionRealization(union_realization)
        if union_realization is not None
        else cfg.union_realization
    )
    adapter = (
        ValidationTimeAdapter
        if union_realization == UnionRealization.VALIDATION
        else ModelConstructionTimeAdapter
    )
    return ty.Annotated[cls, adapter]  # type: ignore[bad-return]


class Union:
    """Annotation used to get the union out of a dynapydantic entity

    This annotation is primarily used for using the union of all models in
    a `TrackingGroup` as a field annotation. It can be used with
    `SubclassTrackingModel`, but in general, `Polymorphic` is preferable.
    """

    @ty.overload
    def __class_getitem__(cls, item: type[ModelT]) -> type[ModelT]: ...

    @ty.overload
    def __class_getitem__(cls, item: TrackingGroup) -> ty.Any: ...  # noqa: ANN401

    def __class_getitem__(cls, item: TrackingGroup | type[ModelT]) -> object:
        """Return the union"""
        return union(item)
