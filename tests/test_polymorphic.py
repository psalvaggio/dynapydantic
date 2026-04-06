"""Unit test for Polymorphic"""

import json
import typing as ty

import pydantic
import pytest

import dynapydantic


class Base(
    dynapydantic.SubclassTrackingModel,
    discriminator_field="name",
    discriminator_value_generator=lambda t: t.__name__,
):
    """Base class"""


class Derived1(Base):
    """A derived class"""

    a: int


class Derived2(Base):
    """A derived class"""

    b: int


class Model(pydantic.BaseModel):
    """Model containing a Polymorphic field"""

    val: dynapydantic.Polymorphic[Base]


def test_polymorphic_parse_python() -> None:
    """Tests the Python parsing functionality of Polymorphic"""
    py_data = {"val": {"name": "Derived1", "a": 2}}
    assert Model.model_validate(py_data) == Model(val=Derived1(a=2))


def test_polymorphic_parse_json() -> None:
    """Tests the JSON parsing functionality of Polymorphic"""
    json_data = '{"val": {"name": "Derived2", "b": 5}}'
    assert Model.model_validate_json(json_data) == Model(val=Derived2(b=5))


def test_polymorphic_serialize_python() -> None:
    """Tests the Python serialization behavior of Polymorphic"""
    assert Model(val=Derived1(a=2)).model_dump() == {
        "val": {"name": "Derived1", "a": 2},
    }


def test_polymorphic_serialize_json() -> None:
    """Tests the Python serialization behavior of Polymorphic"""
    assert json.loads(Model(val=Derived2(b=5)).model_dump_json()) == {
        "val": {"name": "Derived2", "b": 5},
    }


def test_polymorphic_round_trip_python() -> None:
    """Tests the Python round-tripping behavior of Polymorphic"""
    m = Model(val=Derived1(a=2))
    assert Model.model_validate(m.model_dump()) == m


def test_polymorphic_round_trip_json() -> None:
    """Tests the JSON round-tripping behavior of Polymorphic"""
    m = Model(val=Derived1(a=2))
    assert Model.model_validate_json(m.model_dump_json()) == m


def test_polymorphic_with_other_type() -> None:
    """Polymorphic should only work on SubclassTrackingModel's"""
    with pytest.raises(
        pydantic.errors.PydanticSchemaGenerationError,
        match="not a SubclassTrackingModel",
    ):

        class _Model(pydantic.BaseModel):
            field: dynapydantic.Polymorphic[str]  # type: ignore[bad-specialization]

    with pytest.raises(TypeError, match="Polymorphic must be given a type"):

        class _Model(pydantic.BaseModel):
            field: dynapydantic.Polymorphic[5]  # type: ignore[bad-specialization]


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"union_mode": "smart"}, id="smart"),
        pytest.param({"union_mode": "left_to_right"}, id="l2r"),
        pytest.param(
            {
                "discriminator_field": "name",
                "discriminator_value_generator": lambda cls: cls.__name__,
            },
            id="disc",
        ),
    ],
)
def test_single_member_union(kwargs: dict[str, ty.Any]) -> None:
    """Test out a single-member union"""

    class Base(dynapydantic.SubclassTrackingModel):
        tracking_config: ty.ClassVar[dynapydantic.TrackingGroup] = (
            dynapydantic.TrackingGroup(name="test", **kwargs)
        )

    class A(Base):
        a: int

    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[Base]

    assert Model(field={"a": 1}).field == A(a=1)
    with pytest.raises(pydantic.ValidationError):
        Model(field={"a": "foo"})


def test_polymorphic_with_no_registered_subclasses_raises() -> None:
    """Making a union before any subclasses are registered raises aclear error"""

    class EmptyBase(
        dynapydantic.SubclassTrackingModel,
        union_mode="left_to_right",
    ):
        pass

    # No subclasses registered yet
    with pytest.raises(dynapydantic.NoRegisteredTypesError):

        class _M(pydantic.BaseModel):
            val: dynapydantic.Polymorphic[EmptyBase]


def test_polymorphic_model_copy_update() -> None:
    """model_copy(update=) with a Polymorphic field should preserve the type."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    m = Outer(val=A(a=1))
    m2 = m.model_copy(update={"val": B(b=99)})  # bypasses validation
    assert isinstance(m2.val, B)
    assert m2.val == B(b=99)


def test_polymorphic_json_schema_discriminated_union() -> None:
    """Test the JSON schema for a Polymorphic discriminated union."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="kind",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: str

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    schema = Outer.model_json_schema()
    assert "discriminator" in schema["properties"]["val"]
    assert "A" in schema["properties"]["val"]["discriminator"]["mapping"]
    assert "B" in schema["properties"]["val"]["discriminator"]["mapping"]


@pytest.mark.parametrize("union_mode", ["smart", "left_to_right"])
def test_polymorphic_json_schema_smart_union(union_mode: str) -> None:
    """Test the JSON schema for a Polymorphic smart union."""

    class Base(dynapydantic.SubclassTrackingModel, union_mode=union_mode):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: str

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    schema = Outer.model_json_schema()
    assert "anyOf" in schema["properties"]["val"]
    assert {"$ref": "#/$defs/A"} in schema["properties"]["val"]["anyOf"]
    assert {"$ref": "#/$defs/B"} in schema["properties"]["val"]["anyOf"]


def test_polymorphic_strict_validation() -> None:
    """Strict mode should still route correctly via the discriminator."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class A(Base):
        a: int

    class Outer(pydantic.BaseModel):
        val: dynapydantic.Polymorphic[Base]

    result = Outer.model_validate({"val": {"name": "A", "a": 1}}, strict=True)
    assert result.val == A(a=1)

    with pytest.raises(pydantic.ValidationError):
        Outer.model_validate({"val": {"name": "A", "a": "1"}}, strict=True)
