import dynapydantic

from .plugin_classes import Quad, Rectangle, Square


@dynapydantic.hookimpl
def register_models() -> list[dynapydantic.DynamicBaseModel]:
    return [Rectangle, Square, Quad]
