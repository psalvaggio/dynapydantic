import math
import typing as ty

from .shape import Shape

class Circle(Shape):
    type: ty.Literal["Circle"] = "Circle"
    radius: float

    def area(self) -> float:
        return math.pi * self.radius * self.radius
