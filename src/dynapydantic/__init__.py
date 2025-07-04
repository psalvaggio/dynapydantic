"""dynapydantic - dynamic inheritance trees for pydantic models"""

import pluggy

from .base import DynamicBaseModel
from .registry import load_plugins, get_registered_subclasses
from .hookspecs import DynapydanticSpec

hookimpl = pluggy.HookimplMarker("dynapydantic")

__all__ = [
    "DynamicBaseModel",
    "DynapydanticSpec",
    "get_registered_subclasses",
    "hookimpl",
    "load_plugins",
]
