import typing as ty

from .animal import Animal


class Cat(Animal):
    type: ty.Literal["Cat"] = "Cat"
    name: str

    def speak(self) -> str:
        return f"{self.name} says meow"
