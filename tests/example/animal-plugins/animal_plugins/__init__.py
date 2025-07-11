"""Plugin package for animal plugins

This demonstrates using a top-level package import as the plugin entrypoint.
Everything in this file will be registered.
"""

import typing as ty

import base_package


class Dog(base_package.Animal):
    """Dog"""

    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int

    def speak(self) -> str:
        """Speak"""
        return "woof" if self.bark_volume < 50 else "WOOF"


class Horse(base_package.Animal):
    """Horse"""

    type: ty.Literal["Horse"] = "Horse"

    def speak(self) -> str:
        """Speak"""
        return "neigh"
