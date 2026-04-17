"""Custom annotations for dynapydantic"""

import typing as ty

from pydantic import GetCoreSchemaHandler, PydanticSchemaGenerationError
from pydantic_core import core_schema

from .free_funcs import union
from .subclass_tracking_model import SubclassTrackingModel
from .tracking_group import TrackingGroup

ModelT = ty.TypeVar("ModelT", bound=SubclassTrackingModel)


class PydanticAdapter:
    """Pydantic type adapter for SubclassTrackingModel"""

    @staticmethod
    def __get_pydantic_core_schema__(
        source_type: type[SubclassTrackingModel],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Get the pydantic schema for this type"""
        return handler(union(source_type))


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
        """

        def __class_getitem__(cls, item: ModelT) -> ty.Any:  # noqa: ANN401
            """Get the annotation for the pydantic field"""
            if not isinstance(item, type):
                msg = f"dynapydantic.Polymorphic must be given a type, not {item}"
                raise TypeError(msg)

            if getattr(item, "__DYNAPYDANTIC_IMPLICIT_POLYMORPHIC__", False):
                return item

            if not issubclass(item, SubclassTrackingModel):
                msg = (
                    f"Polymorphic was given {item}, which was not a "
                    "SubclassTrackingModel."
                )
                raise PydanticSchemaGenerationError(msg)

            return ty.Annotated[item, PydanticAdapter]


if ty.TYPE_CHECKING:  # pragma: no cover
    ModelT = ty.TypeVar("ModelT", bound=SubclassTrackingModel)

    class Union:
        """Annotation used to get the union out of a dynapydantic entity"""

        @ty.overload
        def __class_getitem__(cls, item: type[ModelT]) -> ModelT: ...

        @ty.overload
        def __class_getitem__(cls, item: TrackingGroup) -> ty.Any: ...  # noqa: ANN401

        def __class_getitem__(cls, item: TrackingGroup | type[ModelT]) -> object:
            """Return the union"""

else:

    class Union:
        """Annotation used to get the union out of a dynapydantic entity"""

        def __class_getitem__(
            cls, item: TrackingGroup | type[SubclassTrackingModel]
        ) -> ty.Any:  # noqa: ANN401
            """Return the union"""
            return union(item)
