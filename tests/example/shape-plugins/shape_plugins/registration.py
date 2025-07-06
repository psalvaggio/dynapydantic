import base_package

from .plugin_classes import Quad, Rectangle, Square


@base_package.Shape.hookimpl
def register_models() -> list[base_package.Shape]:
    return [Rectangle, Square, Quad]
