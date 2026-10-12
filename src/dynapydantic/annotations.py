"""Custom annotations for dynapydantic"""

import typing as ty
import warnings

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


if ty.TYPE_CHECKING:  # pragma: no cover
    ModelConstructionTimeUnion = ty.Annotated[ModelT, ...]
    ValidationTimeUnion = ty.Annotated[ModelT, ...]
else:

    class ModelConstructionTimeUnion:
        """Override the union realization to model-construction time."""

        def __class_getitem__(
            cls,
            item: type[ModelT],
        ) -> ty.Annotated[type[ModelT], ...]:
            """Produce a custom annotation."""
            return ty.Annotated[item, _MODEL_CONSTRUCTION_TIME_UNION]

    class ValidationTimeUnion:
        """Override the union realization to validation time."""

        def __class_getitem__(
            cls,
            item: type[ModelT],
        ) -> ty.Annotated[type[ModelT], ...]:
            """Produce a custom annotation."""
            return ty.Annotated[item, _VALIDATION_TIME_UNION]


# Custom markers for union overrides
_MODEL_CONSTRUCTION_TIME_UNION = object()
_VALIDATION_TIME_UNION = object()


if ty.TYPE_CHECKING:  # pragma: no cover
    Polymorphic = ty.Annotated[ModelT, ...]
else:

    class Polymorphic:
        """Annotation used to mark a type as having duck-typing behavior

        This annotation is only valid for SubclassTrackingModel's.

        Similar to SerializeAsAny, a field annotated with this shall serialize as
        according to its actual type, not the field annotation type. In addition,
        parsing will function as if the field annotation type were the union of
        all tracked subclasses.

        Passing a UnionRealization (or its string value) as a second argument is
        deprecated. Use ModelConstructionTimeUnion or ValidationTimeUnion to
        override the class's default union realization.
        """

        def __class_getitem__(
            cls,
            item: type[ModelT],
        ) -> ty.Annotated[type[ModelT], ...]:
            """Get the annotation for the pydantic field"""
            if isinstance(item, tuple):
                if len(item) > 1:
                    msg = (
                        "The multi-parameter form of Polymorphic is deprecated and "
                        "will be removed in 0.9.0 or 1.0.0, whichever comes first. "
                        "Instead use dynapydantic.ModelConstructionTimeUnion or "
                        "dynapydantic.ValidationTimeUnion."
                    )
                    warnings.warn(msg, DeprecationWarning, stacklevel=2)
                if len(item) > 2:  # noqa: PLR2004
                    msg = (
                        "dynapydantic.Polymorphic takes 1 or 2 arguments "
                        f"({len(item)} given)"
                    )
                    raise TypeError(msg)

                return _polymorphic_cgi(*item)
            return _polymorphic_cgi(item)


def _polymorphic_cgi(
    cls: type[ModelT] | ty.Annotated[type[ModelT], ...],
    union_realization: UnionRealization | str | None = None,
) -> ty.Annotated[type[ModelT], ...]:
    is_annotated = ty.get_origin(cls) is ty.Annotated
    if not isinstance(cls, type) and not is_annotated:
        msg = (
            "dynapydantic.Polymorphic must be given a type or annotated "
            f"type, not {cls}"
        )
        raise TypeError(msg)

    orig_cls = cls
    if is_annotated:
        cls = ty.get_args(cls)[0]

    if not issubclass(cls, SubclassTrackingModel):
        msg = f"Polymorphic was given {cls}, which was not a SubclassTrackingModel."
        raise PydanticSchemaGenerationError(msg)

    cfg = cls.__DYNAPYDANTIC_STM_CONFIG__
    if union_realization is not None:
        union_realization = UnionRealization(union_realization)
    elif is_annotated:
        args = ty.get_args(orig_cls)[1:]
        if _MODEL_CONSTRUCTION_TIME_UNION in args:
            union_realization = UnionRealization.MODEL_CONSTRUCTION
        elif _VALIDATION_TIME_UNION in args:
            union_realization = UnionRealization.VALIDATION
        else:
            union_realization = cfg.union_realization
    else:
        union_realization = cfg.union_realization
    adapter = (
        ValidationTimeAdapter
        if union_realization == UnionRealization.VALIDATION
        else ModelConstructionTimeAdapter
    )
    return ty.Annotated[cls, adapter]  # type: ignore[bad-return]


if ty.TYPE_CHECKING:
    Union = ty.Annotated[ModelT, ...]
else:

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
