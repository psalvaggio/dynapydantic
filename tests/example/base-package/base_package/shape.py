"""Shape base class definition"""

import abc

import dynapydantic


class Shape(
    abc.ABC,
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    plugin_entry_point="shape.plugins",
    discriminator_value_generator=lambda cls: cls.__name__,
):
    """Base class for a shape

    This class is intended to exercise the default discriminator generator
    and plugin discovery
    """

    @abc.abstractmethod
    def area(self) -> float:
        """Compute the area"""
