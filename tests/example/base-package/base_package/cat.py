"""Cat definition"""

import typing as ty

from .animal import Animal


class Cat(Animal):
    """A cat"""

    type: ty.Literal["Cat"] = "Cat"
    name: str

    def speak(self) -> str:
        """Speak"""
        return f"{self.name} says meow"
