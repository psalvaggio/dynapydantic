import abc

import dynapydantic


class Animal(
    abc.ABC,
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    plugin_entry_point="animal.plugins",
):
    @abc.abstractmethod
    def speak(self) -> str:
        pass
