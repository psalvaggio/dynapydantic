"""Unit test for SubclassTrackingModel"""

import datetime
import typing as ty

import pydantic
import pytest

import dynapydantic

from .version_check import skipif_mark_pydantic_version


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


# mode is tested elsewhere
@pytest.mark.parametrize(
    ("data", "kwargs", "truth"),
    [
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"include": {"shape": {"width"}}},
            {
                "shape": {
                    "width": "4.0",
                }
            },
            id="include",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"exclude": {"shape": {"width", "name"}}},
            {
                "shape": {
                    "length": 5.0,
                    "area": 20.0,
                },
                "non_poly_shape": None,
            },
            id="exclude",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"by_alias": True},
            {
                "shape": {
                    "width": "4.0",
                    "height": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": None,
            },
            id="by_alias",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"exclude_unset": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                },
            },
            id="exclude-unset",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"exclude_defaults": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                }
            },
            id="exclude-defaults",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5, "name": None}},
            {"exclude_none": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                }
            },
            id="exclude-none",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"context": {"unit": "m"}},
            {
                "shape": {
                    "width": "4.0 m",
                    "length": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": None,
            },
            id="context",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}},
            {"exclude_computed_fields": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": None,
            },
            marks=[skipif_mark_pydantic_version(lt=(2, 12, 0))],
            id="exclude-computed-fields",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}, "non_poly_shape": {"side": 2}},
            {"serialize_as_any": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": {"side": 2.0},
            },
            marks=[skipif_mark_pydantic_version(ge=(2, 12, 0))],
            id="serialize-as-any-lt-2.12",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}, "non_poly_shape": {"side": 2}},
            {"serialize_as_any": True},
            {
                "shape": {
                    "width": 4.0,
                    "length": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": {"side": 2.0},
            },
            marks=[skipif_mark_pydantic_version(lt=(2, 12, 0), ge=(2, 13, 0))],
            id="serialize-as-any-2.12",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}, "non_poly_shape": {"side": 2}},
            {"serialize_as_any": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": {"side": 2.0},
            },
            marks=[skipif_mark_pydantic_version(lt=(2, 13, 0))],
            id="serialize-as-any-ge-2.13",
        ),
        pytest.param(
            {"shape": {"width": 4, "length": 5}, "non_poly_shape": {"side": 2}},
            {"polymorphic_serialization": True},
            {
                "shape": {
                    "width": "4.0",
                    "length": 5.0,
                    "area": 20.0,
                    "name": "Rectangle",
                },
                "non_poly_shape": {"side": 2.0},
            },
            marks=[skipif_mark_pydantic_version(lt=(2, 13, 0))],
            id="polymorphic-serialziation",
        ),
    ],
)
def test_newer_serialization_options(
    data: dict[str, ty.Any],
    kwargs: dict[str, ty.Any],
    truth: dict[str, ty.Any],
) -> None:
    """Test the serialization options that have been added since 2.0"""

    class Shape(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Rectangle(Shape):
        width: float
        length: float = pydantic.Field(serialization_alias="height")
        name: str | None = "Rectangle"

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

    # Don't slice on the way in
    if "non_poly_shape" in data:
        data["non_poly_shape"] = pydantic.TypeAdapter(
            dynapydantic.Polymorphic[Shape] | None
        ).validate_python(data["non_poly_shape"])

    assert M(**data).model_dump(**kwargs) == truth


def test_validation_time_union_json_schema() -> None:
    """A validation time union should be able to produce a JSON schema"""

    class A(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Model(pydantic.BaseModel):
        a: dynapydantic.Polymorphic[A]

    class B(A):
        b: int

    class C(A):
        c: int

    schema = Model.model_json_schema()
    assert schema["properties"]["a"] == {
        "anyOf": [
            {"$ref": "#/$defs/B"},
            {"$ref": "#/$defs/C"},
        ],
        "title": "A",
    }

    class D(A):
        d: int

    schema = Model.model_json_schema()
    assert schema["properties"]["a"] == {
        "anyOf": [
            {"$ref": "#/$defs/B"},
            {"$ref": "#/$defs/C"},
            {"$ref": "#/$defs/D"},
        ],
        "title": "A",
    }


def test_validation_time_union_json_schema_error() -> None:
    """JSON schema errors should propagate via pydantic errors"""

    class A(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Model(pydantic.BaseModel):
        a: dynapydantic.Polymorphic[A]

    with pytest.raises(
        pydantic.PydanticInvalidForJsonSchema,
        match="no types have been registered yet",
    ):
        Model.model_json_schema()

    class B(A):
        b: int

    Model.model_json_schema()  # should not raise

    # This is an overly paranoid test to hit the KeyError
    with pytest.raises(
        pydantic.PydanticInvalidForJsonSchema,
        match=r"Missing dynapydantic schema metadata\.",
    ):
        Model.model_fields["a"].metadata[0].__get_pydantic_json_schema__({}, None)
