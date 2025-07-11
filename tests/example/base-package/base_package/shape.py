import abc

import dynapydantic


class Shape(
    abc.ABC,
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    plugin_entry_point="shape.plugins",
    discriminator_value_generator=lambda cls: cls.__name__,
):
    @abc.abstractmethod
    def area(self) -> float:
        pass
