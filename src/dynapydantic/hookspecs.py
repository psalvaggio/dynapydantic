"""Plugin specifications for dynapydantic"""

import pluggy

hookspec = pluggy.HookspecMarker("dynapydantic")

class DynapydanticSpec:
    @hookspec
    def register_models() -> list[type]:
        """Return a list of DynamicBaseModel subclasses."""
        pass
