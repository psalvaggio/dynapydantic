"""Unit tests for the generics"""

import dynapydantic


def test_that_generic_subclass_tracking_models_isolate_py312() -> None:
    """Test that generic SubclassTrackingModels isolate registered models"""

    class Base[T2](
        dynapydantic.SubclassTrackingModel,
        discriminator_field="kind",
        discriminator_value_generator=lambda x: x.__name__,
    ):
        """Generic subclass of SubclassTrackingModel"""

        f: T2

    class ConcreteInt(Base[int]):
        """A concrete subclass of Base[int]"""

    class ConcreteStr(Base[str]):
        """A concrete subclass of Base[str]"""

    assert dynapydantic.registered_models(Base[int]) == {"ConcreteInt": ConcreteInt}
    assert dynapydantic.registered_models(Base[str]) == {"ConcreteStr": ConcreteStr}
    assert dynapydantic.registered_models(Base) == {}
