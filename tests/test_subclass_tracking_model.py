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
    assert "C" not in dynapydantic.registered_models(cls)
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

    assert "Concrete" in dynapydantic.registered_models(Base)
    assert "Intermediate" not in dynapydantic.registered_models(Base)


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

    assert list(dynapydantic.registered_models(Base).values()) == [Concrete]


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

    subclasses = dynapydantic.registered_models(FrozenBase)
    assert "Child" in subclasses
    assert "Child2" in subclasses

    c = Child(x=5)
    assert c.model_dump() == {"tag": "Child", "x": 5}
    with pytest.raises(pydantic.ValidationError):
        c.x = 10  # type: ignore[read-only]


@pytest.mark.parametrize(
    "union_realization",
    [None, "model-construction", "validation"],
)
def test_polymorphic_model_dump_json_mode(union_realization: str | None) -> None:
    """model_dump(mode='json') should propagate through our unions"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        union_realization=union_realization,
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


def test_root_in_union() -> None:
    """Test that the inheritance tree root can be in the union"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        exclude_from_union=False,
    ):
        a: int

    class B(Base):
        b: int

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    assert Outer(val={"name": "Base", "a": 1}).val == Base(a=1)
    assert Outer(val={"name": "B", "a": 2, "b": 3}).val == B(a=2, b=3)


def test_eager_union() -> None:
    """Test that eager union evaluation works"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
    ):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Union[Base]

    m = Outer(val=A(a=1))
    assert m.val == A(a=1)
    m = Outer(val=B(b=2))
    assert m.val == B(b=2)


@pytest.mark.parametrize("val", ["foo", 1])
def test_invalid_union_realization(val: int | str) -> None:
    """Test an invalid value for the the union_realization parameter"""
    with pytest.raises(
        dynapydantic.ConfigurationError, match="invalid union_realization"
    ):

        class Base(
            dynapydantic.SubclassTrackingModel,
            union_mode="smart",
            union_realization=val,
        ):
            pass


def test_validation_time_union_no_members() -> None:
    """An error is risen at validation time when no subclasses exist"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[Base]

    with pytest.raises(
        pydantic.ValidationError,
        match=r"(?s)field.*Unable to produce a union.*dynapydantic_error",
    ):
        Model(field={"some": "dummy value"})


def test_json_serialization_exclude_options() -> None:
    """Test that serialization options are correctly propagated"""

    class MyBase(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        some_value: str = "Some Value"

    class Foo(MyBase):
        base: MyBase
        poly_base: dynapydantic.Polymorphic[MyBase]
        none: None = None

    class Bar(MyBase):
        hello: str = pydantic.Field(default="Hello", alias="hi")
        world: str = "World"

    test1 = Foo(
        base=Bar(world="Expected to be sliced (pydantic's fault)"),
        poly_base=Bar(world="Expected in output (poly_base)"),
    )

    # Test propagation of exclude_defaults and indent
    assert (
        test1.model_dump_json(indent=2, exclude_defaults=True)
        == """{
  "base": {},
  "poly_base": {
    "world": "Expected in output (poly_base)"
  }
}"""
    )

    # Test propagation of exclude
    assert test1.model_dump_json(exclude={"poly_base": {"world"}}) == (
        '{"some_value":"Some Value",'
        '"base":{"some_value":"Some Value"},'
        '"poly_base":{"some_value":"Some Value","hello":"Hello"},'
        '"none":null}'
    )

    # Test propagation of include and by_alias
    assert test1.model_dump(include={"poly_base": {"hello"}}, by_alias=True) == {
        "poly_base": {"hi": "Hello"}
    }

    # Test propagation of exclude_unset
    assert test1.model_dump(exclude_unset=True) == {
        "base": {},
        "poly_base": {"world": "Expected in output (poly_base)"},
    }


def test_newer_serialization_options() -> None:
    """Test the serialization options that have been added since 2.0"""

    class Shape(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Rectangle(Shape):
        width: float
        length: float

        @pydantic.computed_field
        @property
        def area(self) -> float:
            return self.width * self.length

        @pydantic.field_serializer("width")
        def serialize_courses_in_order(
            self,
            width: float,
            info: pydantic.SerializationInfo,
        ) -> str:
            if info.context is not None:
                return f"{width} {info.context['unit']}"
            return str(width)

    class Square(Shape):
        side: float

    class M(pydantic.BaseModel):
        shape: dynapydantic.Polymorphic[Shape]
        non_poly_shape: Shape | None = None

    # Test context
    assert M(shape=Rectangle(width=4, length=5)).model_dump(
        context={"unit": "m"}, exclude_none=True
    ) == {
        "shape": {
            "width": "4.0 m",
            "length": 5.0,
            "area": 20.0,
        }
    }

    # Test exclude_computed_fields and serialize_as_any
    assert M(
        shape=Rectangle(width=4, length=5), non_poly_shape=Square(side=2)
    ).model_dump(exclude_computed_fields=True, serialize_as_any=True) == {
        "shape": {
            "width": "4.0",
            "length": 5.0,
        },
        "non_poly_shape": {"side": 2.0},
    }

    # Test polymorphic_serialization
    assert M(
        shape=Rectangle(width=4, length=5), non_poly_shape=Square(side=2)
    ).model_dump(polymorphic_serialization=True) == {
        "shape": {
            "width": "4.0",
            "length": 5.0,
            "area": 20.0,
        },
        "non_poly_shape": {"side": 2.0},
    }
