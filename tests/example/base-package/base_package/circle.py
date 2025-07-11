"""Circle definition"""

import math

from .shape import Shape


class Circle(Shape):
    """A circle"""

    radius: float

    def area(self) -> float:
        """Compute the area"""
        return math.pi * self.radius * self.radius
