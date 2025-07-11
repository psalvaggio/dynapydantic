"""Unit test for SubclassTrackingModel"""

import typing as ty

import pydantic
import pytest

import dynapydantic


class SimpleKwargBase(dynapydantic.SubclassTrackingModel, discriminator_field="name"):
    """Initialize the TrackingGroup via kwargs"""

    a: int


class SimpleConfigBase(dynapydantic.SubclassTrackingModel):
    """Initialize the TrackingGroup via a class var"""

    tracking_config: ty.ClassVar[dynapydantic.TrackingGroup] = (
        dynapydantic.TrackingGroup(
            name="SimpleConfigBase-subclasses",
            discriminator_field="name",
        )
    )

    a: int


@pytest.mark.parametrize("cls", [SimpleKwargBase, SimpleConfigBase])
def test_basic(cls: type[dynapydantic.SubclassTrackingModel]) -> None:
    """Test the basic usage of SubclassTrackingModel"""

    class Derived1(cls):
        name: ty.Literal["A"] = "A"
        b: int

    class Derived2(cls):
        name: ty.Literal["B"] = "B"
        b: int

    class Derived3(cls, exclude_from_union=True):
        name: ty.Literal["C"] = "C"
        b: int

    assert not hasattr(cls, "load_plugins")

    class Parse(pydantic.RootModel):
        root: cls.union()

    assert Parse.model_validate({"name": "A", "a": 1, "b": 2}).root == Derived1(
        a=1,
        b=2,
    )
    assert Parse.model_validate({"name": "B", "a": 1, "b": 2}).root == Derived2(
        a=1,
        b=2,
    )
    assert "C" not in cls.registered_subclasses()


def test_no_config_raises() -> None:
    """No tracking config -> error"""
    with pytest.raises(dynapydantic.ConfigurationError):

        class Bad(dynapydantic.SubclassTrackingModel):
            pass
