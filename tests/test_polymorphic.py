"""Unit test for Polymorphic"""

import json
import typing as ty
import warnings

import pydantic
import pytest

import dynapydantic
from dynapydantic.annotations import ModelConstructionTimeAdapter


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


def test_polymorphic_accepts_single_parameter_tuple_without_warning() -> None:
    """A one-item tuple remains an un-deprecated spelling of the type."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        annotation = dynapydantic.Polymorphic[Base,]

    assert ty.get_args(annotation)[1] is ModelConstructionTimeAdapter
    assert not caught


def test_polymorphic_unknown_annotated_marker_uses_model_default() -> None:
    """Unknown metadata is preserved without changing union realization."""
    annotation = dynapydantic.Polymorphic[ty.Annotated[Base, "unknown"]]

    assert ty.get_args(annotation) == (
        Base,
        "unknown",
        ModelConstructionTimeAdapter,
    )


@pytest.mark.parametrize(
    "union_annotation",
    [
        dynapydantic.ModelConstructionTimeUnion,
        dynapydantic.ValidationTimeUnion,
    ],
)
def test_polymorphic_preserves_field_metadata(
    union_annotation: ty.Any,  # noqa: ANN401 (no great way to annotate this)
) -> None:
    """Field metadata survives both union override annotations."""

    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[
            union_annotation[
                ty.Annotated[Base, pydantic.Field(description="Base value")]
            ]
        ]

    assert Model.model_json_schema()["properties"]["field"]["description"] == (
        "Base value"
    )


def test_polymorphic_rejects_conflicting_union_realization_markers() -> None:
    """A single annotation cannot request both union realization modes."""
    with pytest.raises(TypeError, match="Conflicting union realization overrides"):
        dynapydantic.Polymorphic[
            dynapydantic.ModelConstructionTimeUnion[
                dynapydantic.ValidationTimeUnion[Base]
            ]
        ]


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


def test_polymorphic_union_realization_overrides_class_default() -> None:
    """Test override behavior of Polymorphic's union realization"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization=dynapydantic.UnionRealization.VALIDATION,
    ):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int
        other: dynapydantic.Polymorphic[dynapydantic.ModelConstructionTimeUnion[Base]]

    # No B in the schema because the union was eaglerly made
    b_schema = B.model_json_schema()
    assert b_schema["properties"]["other"] == {"$ref": "#/$defs/A"}

    class DynamicBase(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization=dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
    ):
        pass

    class DynamicA(DynamicBase):
        a: int

    class Outer(pydantic.BaseModel):
        other: dynapydantic.Polymorphic[dynapydantic.ValidationTimeUnion[DynamicBase]]

    class DynamicB(DynamicBase):
        b: int

    assert Outer(other={"b": 2}).other == DynamicB(b=2)


def test_polymorphic_deprecated_union_realization_override() -> None:
    """The deprecated multi-parameter form still works and warns."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization=dynapydantic.UnionRealization.VALIDATION,
    ):
        pass

    class A(Base):
        a: int

    with pytest.warns(FutureWarning, match="multi-parameter form"):

        class B(Base):
            b: int
            other: dynapydantic.Polymorphic[  # type: ignore[bad-specialization]
                Base,
                dynapydantic.UnionRealization.MODEL_CONSTRUCTION,  # type: ignore[not-a-type, ty:invalid-type-arguments, ty:invalid-type-form]
            ]

    schema = B.model_json_schema()
    assert schema["properties"]["other"] == {"$ref": "#/$defs/A"}


def test_incorrect_num_args() -> None:
    """Test passing the incorrect number of arguments to Polymorphic"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    with (
        pytest.raises(TypeError, match="Polymorphic takes 1 or 2 arguments"),
    ):
        dynapydantic.Polymorphic.__class_getitem__(
            ty.cast("ty.Any", (Base, "validation", "foo")),
        )


@pytest.mark.parametrize(
    "inner_type",
    [
        5,
        int,
        list[int],
        pydantic.BaseModel,
        ty.Annotated[pydantic.BaseModel, list[int]],
    ],
)
def test_polymorphic_rejects_invalid_inner_types(
    inner_type: ty.Any,  # noqa: ANN401
) -> None:
    """Polymorphic rejects the inner types with the correct message."""
    with pytest.raises(
        pydantic.PydanticSchemaGenerationError, match="Polymorphic was given"
    ):

        class Model(pydantic.BaseModel):
            field: dynapydantic.Polymorphic[inner_type]
