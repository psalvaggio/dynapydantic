"""Animal base class"""

import abc

import dynapydantic


class Animal(
    abc.ABC,
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    plugin_entry_point="animal.plugins",
):
    """An animal base class

    This is intended to excercise the kwarg initialization of the tracking
    group and plugin discovery
    """

    @abc.abstractmethod
    def speak(self) -> str:
        """Speak"""
