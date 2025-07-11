"""Shape plugin classes"""

import typing as ty

import base_package


class Quad(base_package.Shape, exclude_from_union=True):
    """Intermediate class not to be included in the union"""


class Rectangle(Quad):
    """A rectangle"""

    type: ty.Literal["Rect"] = "Rect"
    length: float
    width: float

    def area(self) -> float:
        """Compute the area"""
        return self.length * self.width


class Square(Quad):
    """A square"""

    side: float

    def area(self) -> float:
        """Compute the area"""
        return self.side * self.side
