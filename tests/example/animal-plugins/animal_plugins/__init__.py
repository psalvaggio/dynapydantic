import typing as ty

import base_package

class Dog(base_package.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> None:
        print("woof" if self.bark_volume < 50 else "WOOF")

class Horse(base_package.Animal):
    type: ty.Literal["Horse"] = "Horse"

    def speak(self) -> None:
        print("neigh")

# A no-op hook like this does not need to be explicitly defined
#@base_package.Animal.hookimpl
#def register_models() -> None:
    #pass
