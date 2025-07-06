import abc

import dynapydantic

class Shape(abc.ABC, dynapydantic.DynamicBaseModel, discriminator_field="type"):
    @abc.abstractmethod
    def area(self) -> float:
        pass
