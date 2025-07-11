import typing as ty

import base_package

class Dog(base_package.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> str:
        return "woof" if self.bark_volume < 50 else "WOOF"

class Horse(base_package.Animal):
    type: ty.Literal["Horse"] = "Horse"

    def speak(self) -> str:
        return "neigh"
