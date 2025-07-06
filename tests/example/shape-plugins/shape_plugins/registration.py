import typing as ty

import base_package


def register_models() -> None:
    from .plugin_classes import Quad, Rectangle, Square

    class Triangle(base_package.Shape):
        type: ty.Literal["Triangle"] = "Triangle"
        base: float
        height: float

        def area(self) -> float:
             return 0.5 * self.base * self.height
