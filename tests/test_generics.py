"""Unit tests for the generics"""

import typing as ty

import pydantic

import dynapydantic

T = ty.TypeVar("T")


def test_generic_subclass_tracking_model_basic() -> None:
    """Test that a generic SubclassTrackingModel passes a basic smoke test"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        ty.Generic[T],
        discriminator_field="kind",
    ):
        """Generic subclass of SubclassTrackingModel"""

        f: T

    class Model(pydantic.BaseModel):
        a: int

    class Concrete(Base[Model]):
        """A concrete subclass of Base[Model]"""

        kind: ty.Literal["concrete"] = "concrete"

    assert dynapydantic.registered_models(Base[Model]) == {"concrete": Concrete}
    assert dynapydantic.registered_models(Base) == {}


def test_generic_subclass_tracking_model_basic_value_gen() -> None:
    """Test that a generic SubclassTrackingModel passes a basic smoke test"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        ty.Generic[T],
        discriminator_field="kind",
        discriminator_value_generator=lambda x: x.__name__,
    ):
        """Generic subclass of SubclassTrackingModel"""

        f: T

    class Model(pydantic.BaseModel):
        a: int

    class Concrete(Base[Model]):
        """A concrete subclass of Base[Model]"""

    assert dynapydantic.registered_models(Base[Model]) == {"Concrete": Concrete}
    assert dynapydantic.registered_models(Base) == {}


def test_that_generic_subclass_tracking_models_isolate() -> None:
    """Test that generic SubclassTrackingModels isolate registered models"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        ty.Generic[T],
        discriminator_field="kind",
        discriminator_value_generator=lambda x: x.__name__,
    ):
        """Generic subclass of SubclassTrackingModel"""

        f: T

    class ConcreteInt(Base[int]):
        """A concrete subclass of Base[int]"""

    class ConcreteStr(Base[str]):
        """A concrete subclass of Base[str]"""

    assert dynapydantic.registered_models(Base[int]) == {"ConcreteInt": ConcreteInt}
    assert dynapydantic.registered_models(Base[str]) == {"ConcreteStr": ConcreteStr}
    assert dynapydantic.registered_models(Base) == {}


def test_multilayer_generic() -> None:
    """Test the behavior of multiple generics in an inheritance tree"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        ty.Generic[T],
        discriminator_field="kind",
        discriminator_value_generator=lambda x: x.__name__,
    ):
        """Generic subclass of SubclassTrackingModel"""

        f: T

    class ConcreteInt(Base[int]):
        """A concrete subclass of Base[int]"""

    class GenericMid(ConcreteInt, ty.Generic[T]):
        """An intermediate generic base"""

        f2: T

    class ConcreteInt2(GenericMid[int]):
        """A concrete subclass of GenericMid[int]"""

    class ConcreteStr(GenericMid[str]):
        """A concrete subclass of GenericMid[str]"""

    assert dynapydantic.registered_models(Base[int]) == {
        "ConcreteInt": ConcreteInt,
        "GenericMid[int]": GenericMid[int],
        "GenericMid[str]": GenericMid[str],
        "ConcreteInt2": ConcreteInt2,
        "ConcreteStr": ConcreteStr,
    }
    assert dynapydantic.registered_models(Base[str]) == {}
    assert dynapydantic.registered_models(GenericMid) == {}
    assert dynapydantic.registered_models(GenericMid[int]) == {
        "GenericMid[int]": GenericMid[int],
        "ConcreteInt2": ConcreteInt2,
    }
    assert dynapydantic.registered_models(GenericMid[str]) == {
        "GenericMid[str]": GenericMid[str],
        "ConcreteStr": ConcreteStr,
    }
    assert dynapydantic.registered_models(Base) == {}
