"""Base package to demonstrate plugin discovery"""

import dynapydantic

from .animal import Animal
from .cat import Cat
from .circle import Circle
from .shape import Shape

dynapydantic.load_plugins(Animal)
dynapydantic.load_plugins(Shape)

__all__ = [
    "Animal",
    "Cat",
    "Circle",
    "Shape",
]
