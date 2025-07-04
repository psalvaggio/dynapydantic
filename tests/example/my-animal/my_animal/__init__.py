import dynapydantic

from .animal import Animal
from .cat import Cat

@dynapydantic.hookimpl
def register_models() -> list[dynapydantic.DynamicBaseModel]:
    return [Animal]

dynapydantic.load_plugins()
