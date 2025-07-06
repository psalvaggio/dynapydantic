import abc

import dynapydantic


class Animal(
    abc.ABC,
    dynapydantic.DynamicBaseModel,
    discriminator_field="type",
    plugin_entry_point="animal.plugins",
):
    @abc.abstractmethod
    def speak(self) -> None:
        pass
