import dynapydantic

from .animal import Animal
from .cat import Cat
from .circle import Circle
from .shape import Shape

@dynapydantic.hookimpl
def register_models() -> list[dynapydantic.DynamicBaseModel]:
    return [Animal]

dynapydantic.load_plugins()
