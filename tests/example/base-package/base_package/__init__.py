"""Base package to demonstrate plugin discovery"""

from .animal import Animal
from .cat import Cat
from .circle import Circle
from .shape import Shape

Animal.load_plugins()
Shape.load_plugins()

__all__ = [
    "Animal",
    "Cat",
    "Circle",
    "Shape",
]
