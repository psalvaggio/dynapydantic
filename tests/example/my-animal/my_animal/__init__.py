import abc
import typing as ty

import dynapydantic
import pluggy

class Animal(abc.ABC, dynapydantic.DynamicBaseModel, discriminator_field="type"):
    @abc.abstractmethod
    def speak(self) -> None:
        pass

class Cat(Animal):
    type: ty.Literal["Cat"] = "Cat"
    name: str

    def speak(self) -> None:
        print(f"{self.name} says meow")

@dynapydantic.hookimpl
def register_models() -> list[dynapydantic.DynamicBaseModel]:
    return [Animal]

dynapydantic.load_plugins()
