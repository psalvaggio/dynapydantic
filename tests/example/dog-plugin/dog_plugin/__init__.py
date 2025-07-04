import typing as ty

import my_animal
import pluggy

hookimpl = pluggy.HookimplMarker("dynapydantic")

class Dog(my_animal.Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> None:
        print("woof" if self.bark_volume < 50 else "WOOF")

@hookimpl
def register_models() -> list[my_animal.Animal]:
    return [Dog]
