"""Definition for Polymorphic"""

import typing as ty

from .subclass_tracking_model import SubclassTrackingModel

ModelT = ty.TypeVar("ModelT", bound=SubclassTrackingModel)

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
            return ty.Annotated[item, SubclassTrackingModel.PydanticAdaptor]
