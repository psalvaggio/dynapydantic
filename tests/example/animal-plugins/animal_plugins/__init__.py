import typing as ty

import base_package

class Dog(base_package.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> None:
        print("woof" if self.bark_volume < 50 else "WOOF")

@base_package.Animal.hookimpl
def register_models() -> list[base_package.Animal]:
    return [Dog]
