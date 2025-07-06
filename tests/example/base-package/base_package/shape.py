import abc

import dynapydantic


class Shape(
    abc.ABC,
    dynapydantic.DynamicBaseModel,
    discriminator_field="type",
    pluggy_hook="shape.plugins",
):
    @abc.abstractmethod
    def area(self) -> float:
        pass
