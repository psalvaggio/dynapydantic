import abc

import dynapydantic

class Animal(abc.ABC, dynapydantic.DynamicBaseModel, discriminator_field="type"):
    @abc.abstractmethod
    def speak(self) -> None:
        pass
