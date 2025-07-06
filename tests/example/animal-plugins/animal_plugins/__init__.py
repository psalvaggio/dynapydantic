import typing as ty

import base_package
import dynapydantic

class Dog(base_package.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> None:
        print("woof" if self.bark_volume < 50 else "WOOF")

@dynapydantic.hookimpl
def register_models() -> list[dynapydantic.DynamicBaseModel]:
    return [Dog]
