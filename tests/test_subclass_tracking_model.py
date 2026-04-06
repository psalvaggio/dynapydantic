"""Unit test for SubclassTrackingModel"""

import datetime
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
        root: dynapydantic.Polymorphic[cls]

    assert Parse.model_validate({"name": "A", "a": 1, "b": 2}).root == Derived1(
        a=1,
        b=2,
    )
    assert Parse.model_validate({"name": "B", "a": 1, "b": 2}).root == Derived2(
        a=1,
        b=2,
    )
    assert "C" not in cls.registered_subclasses()
    with pytest.raises(
        pydantic.ValidationError,
        match="does not match any of the expected tags",
    ):
        Parse.model_validate({"name": "C", "b": 5})


def test_no_config_raises() -> None:
    """No tracking config -> error"""
    with pytest.raises(dynapydantic.ConfigurationError):

        class Bad(dynapydantic.SubclassTrackingModel):
            pass


def test_smart_union() -> None:
    """Test a smart union"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        a: int
        b: int

    assert pydantic.TypeAdapter(dynapydantic.Polymorphic[Base]).validate_python(
        {"a": 1, "b": 5}
    ) == B(a=1, b=5)


def test_l2r_union() -> None:
    """Test a left-to-right union"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="left_to_right"):
        pass

    class A(Base):
        a: int

    class B(Base):
        a: int
        b: int

    assert pydantic.TypeAdapter(dynapydantic.Polymorphic[Base]).validate_python(
        {"a": 1, "b": 5}
    ) == A(a=1)


def test_invalid_union_modes() -> None:
    """Test what happens if the user misconfigures the union mode"""
    with pytest.raises(dynapydantic.ConfigurationError, match="union_mode"):

        class Base(dynapydantic.SubclassTrackingModel, union_mode="foo"):
            pass


def test_three_level_subclass_hierarchy() -> None:
    """Concrete grandchild should register in the base's TrackingGroup."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class Intermediate(Base, exclude_from_union=True):
        pass

    class Concrete(Intermediate):
        x: int

    assert "Concrete" in Base.registered_subclasses()
    assert "Intermediate" not in Base.registered_subclasses()


def test_diamond_inheritance_no_duplicate_registration() -> None:
    """A class that appears twice in the MRO should only be registered once."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class Mixin(Base, exclude_from_union=True):
        pass

    class Mixin2(Base, exclude_from_union=True):
        pass

    class Concrete(Mixin, Mixin2):
        x: int

    assert list(Base.registered_subclasses().values()) == [Concrete]


def test_tracking_config_classvar_takes_precedence_over_kwargs() -> None:
    """tracking_config should take priority over class kwargs"""
    tc = dynapydantic.TrackingGroup(
        name="explicit-config",
        discriminator_field="kind",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="IGNORED",  # should be silently ignored
    ):
        tracking_config: ty.ClassVar[dynapydantic.TrackingGroup] = tc

    class A(Base):
        pass

    assert A().model_dump() == {"kind": "A"}


def test_subclass_tracking_with_frozen_base() -> None:
    """A frozen SubclassTrackingModel base should still register subclasses."""

    class FrozenBase(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="tag",
        discriminator_value_generator=lambda cls: cls.__name__,
        frozen=True,
    ):
        pass

    class Child(FrozenBase):
        x: int

    class Child2(FrozenBase):
        y: int

    assert "Child" in FrozenBase.registered_subclasses()
    assert "Child2" in FrozenBase.registered_subclasses()

    c = Child(x=5)
    assert c.model_dump() == {"tag": "Child", "x": 5}
    with pytest.raises(pydantic.ValidationError):
        c.x = 10  # type: ignore[read-only]


def test_polymorphic_model_dump_json_mode() -> None:
    """model_dump(mode='json') should propagate through our unions"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class A(Base):
        a: int
        created_at: datetime.datetime

    class B(Base):
        b: int

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    m = Outer(
        val=A(
            a=1, created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        )
    )
    dumped = m.model_dump(mode="json")
    assert dumped["val"]["created_at"] == "2024-01-01T00:00:00Z"
    assert dumped["val"]["a"] == 1
