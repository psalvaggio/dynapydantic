import abc

import dynapydantic


class Animal(
    abc.ABC,
    dynapydantic.DynamicBaseModel,
    discriminator_field="type",
    pluggy_hook="animal.plugins",
):
    @abc.abstractmethod
    def speak(self) -> None:
        pass
