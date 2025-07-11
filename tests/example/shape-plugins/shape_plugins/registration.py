"""Entrypoint for registering plugins"""

import base_package


def register_models() -> None:
    """Entrypoint for registering plugins"""
    from .plugin_classes import Quad, Rectangle, Square  # noqa: F401, PLC0415

    class Triangle(base_package.Shape):
        base: float
        height: float

        def area(self) -> float:
            return 0.5 * self.base * self.height
