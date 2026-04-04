"""Union mode configuration types for dynapydantic."""

import typing as ty
from collections.abc import Callable

import pydantic


class DiscriminatedConfig(pydantic.BaseModel, frozen=True, extra="forbid"):
    """Configuration for a discriminated union.

    Carries the discriminator field name and optional value generator that
    are required when pydantic's discriminated-union validation strategy is
    used.
    """

    discriminator_field: str = pydantic.Field(
        description="Name of the field used to discriminate between subtypes.",
    )
    discriminator_value_generator: Callable[[type], str] | None = pydantic.Field(
        None,
        description=(
            "A callable that produces default values for the discriminator "
            "field when none is supplied via register()."
        ),
    )


#: Literal type for the two non-discriminated union strategies.
NonDiscriminatedMode = ty.Literal["smart", "left_to_right"]

#: Full union-mode type.  Either a structured `DiscriminatedMode`
#: (the default) or one of the plain string literals for the two
#: non-discriminated strategies.
UnionMode = DiscriminatedConfig | NonDiscriminatedMode
