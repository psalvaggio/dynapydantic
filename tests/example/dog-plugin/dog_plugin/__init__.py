import typing as ty

import dynapydantic
import my_animal

class Dog(my_animal.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> None:
        print("woof" if self.bark_volume < 50 else "WOOF")

@dynapydantic.hookimpl
def register_models() -> list[my_animal.Animal]:
    return [Dog]
