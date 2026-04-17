"""Tests for the implicit_polymorphic option on SubclassTrackingModel"""

import datetime

import pydantic
import pytest

import dynapydantic

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _make_discriminated_base() -> type[dynapydantic.SubclassTrackingModel]:
    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="kind",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        """Base class for a discriminated union"""

    return Base


def _make_smart_base() -> type[dynapydantic.SubclassTrackingModel]:
    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        implicit_polymorphic=True,
    ):
        """Base class for a discriminated union"""

    return Base


# ===========================================================================
# 1.  Direct field annotation (no Polymorphic) — the core ergonomics test
# ===========================================================================


def test_discriminated_subclass_resolved_via_base_annotation() -> None:
    """Fields typed as the base class validate to the correct subclass."""
    base = _make_discriminated_base()

    class Child(base):
        value: int

    class Container(pydantic.BaseModel):
        item: base

    result = Container.model_validate({"item": {"kind": "Child", "value": 7}})
    assert isinstance(result.item, Child)
    assert result.item.value == 7


def test_smart_union_subclass_resolved_via_base_annotation() -> None:
    """Smart-mode base field resolves the correct subclass without discriminator."""
    base = _make_smart_base()

    class OnlyInt(base):
        x: int

    class Container(pydantic.BaseModel):
        item: base

    result = Container.model_validate({"item": {"x": 3}})
    assert isinstance(result.item, OnlyInt)
    assert result.item.x == 3


def test_invalid_data_raises_validation_error() -> None:
    """Invalid data still raises ``pydantic.ValidationError``."""
    base = _make_discriminated_base()

    class Child(base):
        value: int

    class Container(pydantic.BaseModel):
        item: base

    with pytest.raises(pydantic.ValidationError):
        Container.model_validate({"item": {"kind": "NonExistent", "value": 1}})


# ===========================================================================
# 2.  Lazy registration — subclass added *after* the containing model is built
# ===========================================================================


def test_late_subclass_is_picked_up_without_model_rebuild() -> None:
    """A subclass defined after the container validates on the next call."""
    base = _make_discriminated_base()

    class Container(pydantic.BaseModel):
        item: base

    # Container is fully compiled *before* LateChild exists.
    class LateChild(base):
        score: float

    result = Container.model_validate({"item": {"kind": "LateChild", "score": 9.5}})
    assert isinstance(result.item, LateChild)
    assert result.item.score == pytest.approx(9.5)


def test_multiple_late_subclasses_all_visible() -> None:
    """Several subclasses added after container build are each reachable."""
    base = _make_discriminated_base()

    class Container(pydantic.BaseModel):
        item: base

    class Alpha(base):
        a: str

    class Beta(base):
        b: str

    alpha = Container.model_validate({"item": {"kind": "Alpha", "a": "hello"}})
    beta = Container.model_validate({"item": {"kind": "Beta", "b": "world"}})

    assert isinstance(alpha.item, Alpha)
    assert isinstance(beta.item, Beta)


def test_generation_advances_on_each_new_registration() -> None:
    """``TrackingGroup._generation`` increments for every new subclass."""
    base = _make_discriminated_base()
    initial = base.__DYNAPYDANTIC__._generation  # noqa: SLF001

    class C1(base):
        x: int

    assert base.__DYNAPYDANTIC__.generation == initial + 1

    class C2(base):
        y: int

    assert base.__DYNAPYDANTIC__.generation == initial + 2


# ===========================================================================
# 3.  Serialisation round-trip
# ===========================================================================


def test_model_dump_preserves_subclass_fields() -> None:
    """``model_dump()`` on the container exposes subclass-specific fields."""
    base = _make_discriminated_base()

    dt_str = "2026-04-16T21:42:00Z"
    dt = datetime.datetime.fromisoformat(dt_str)

    class Child(base):
        payload: datetime.datetime

    class Container(pydantic.BaseModel):
        item: base

    obj = Container(item={"kind": "Child", "payload": dt})
    dumped = obj.model_dump()
    assert dumped == {"item": {"kind": "Child", "payload": dt}}
    dumped_json = obj.model_dump(mode="json")
    assert dumped_json == {"item": {"kind": "Child", "payload": dt_str}}


def test_round_trip_json() -> None:
    """JSON serialisation + deserialisation preserves type and values."""
    base = _make_discriminated_base()

    class Child(base):
        number: int

    class Container(pydantic.BaseModel):
        item: base

    original = Container.model_validate({"item": {"kind": "Child", "number": 42}})
    json_str = original.model_dump_json()
    restored = Container.model_validate_json(json_str)

    assert isinstance(restored.item, Child)
    assert restored.item.number == 42


def test_round_trip_already_instantiated_object() -> None:
    """Passing an already-constructed subclass instance into model_validate works."""
    base = _make_discriminated_base()

    class Child(base):
        tag: str

    class Container(pydantic.BaseModel):
        item: base

    child_obj = Child(tag="hello")
    container = Container(item=child_obj)
    assert isinstance(container.item, Child)
    assert container.item.tag == "hello"


# ===========================================================================
# 4.  Backward-compat: Polymorphic still works unchanged
# ===========================================================================


def test_polymorphic_annotation_resolves_subclass() -> None:
    """Explicit Polymorphic annotation resolves subclass correctly."""
    base = _make_discriminated_base()

    class Child(base):
        v: int

    class Container(pydantic.BaseModel):
        item: dynapydantic.Polymorphic[base]

    result = Container.model_validate({"item": {"kind": "Child", "v": 99}})
    assert isinstance(result.item, Child)
    assert result.item.v == 99


def test_polymorphic_picks_up_late_subclass() -> None:
    """With Polymorphic, late-registered subclass is also picked up lazily."""
    base = _make_discriminated_base()

    class Container(pydantic.BaseModel):
        item: dynapydantic.Polymorphic[base]

    class LateChild(base):
        z: bool

    result = Container.model_validate({"item": {"kind": "LateChild", "z": True}})
    assert isinstance(result.item, LateChild)
    assert result.item.z is True


# ===========================================================================
# 5.  Edge cases
# ===========================================================================


def test_base_with_no_subclasses_raises_on_validate() -> None:
    """Validating when no subclasses are registered raises ValidationError."""
    base = _make_discriminated_base()

    class Container(pydantic.BaseModel):
        item: base

    with pytest.raises(pydantic.ValidationError):
        Container.model_validate({"item": {"kind": "Ghost", "x": 1}})


def test_multiple_containers_share_same_adapter_cache() -> None:
    """Two unrelated containers referencing the same base share the adapter."""
    base = _make_discriminated_base()

    class Child(base):
        n: int

    class ContainerA(pydantic.BaseModel):
        item: base

    class ContainerB(pydantic.BaseModel):
        item: base

    ContainerA.model_validate({"item": {"kind": "Child", "n": 1}})
    adapter_a = base.__DYNAPYDANTIC__.type_adapter

    ContainerB.model_validate({"item": {"kind": "Child", "n": 2}})
    adapter_b = base.__DYNAPYDANTIC__.type_adapter

    # Both containers use the same cached TypeAdapter on the base class
    assert adapter_a is adapter_b


def test_exclude_from_union_still_excluded() -> None:
    """``exclude_from_union=True`` subclasses are never dispatched to."""
    base = _make_discriminated_base()

    class Excluded(base, exclude_from_union=True):
        secret: str

    class Container(pydantic.BaseModel):
        item: base

    with pytest.raises(pydantic.ValidationError):
        Container.model_validate({"item": {"kind": "Excluded", "secret": "shh"}})


@pytest.mark.parametrize(
    "union_mode",
    [
        pytest.param("smart", id="smart"),
        pytest.param("left_to_right", id="left-to-right"),
    ],
)
def test_non_discriminated_modes_also_lazy(union_mode: str) -> None:
    """Smart and left_to_right union modes are also lazily rebuilt."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode=union_mode,
        implicit_polymorphic=True,
    ):
        pass

    class Container(pydantic.BaseModel):
        item: Base

    class OnlyChild(Base):
        q: int

    result = Container.model_validate({"item": {"q": 11}})
    assert isinstance(result.item, OnlyChild)
    assert result.item.q == 11


def test_json_schema_works_on_simple_smart_union() -> None:
    """JSON schema works on a simple two-member smart union"""
    base = _make_smart_base()

    class Container(pydantic.BaseModel):
        item: base

    class Child1(base, extra="forbid"):
        a: int

    class Child2(base, extra="forbid"):
        b: int

    js = Container.model_json_schema()
    assert js["properties"]["item"] == {
        "anyOf": [
            {"$ref": "#/$defs/Child1"},
            {"$ref": "#/$defs/Child2"},
        ],
        "title": "Item",
    }


# ===========================================================================
# 6.  Error Behavior
# ===========================================================================


def test_validation_error_good_message_on_smart_union() -> None:
    """The validation error should still be good (smart union)"""
    base = _make_smart_base()

    class Container(pydantic.BaseModel):
        item: base

    class Child1(base, extra="forbid"):
        a: int

    class Child2(base, extra="forbid"):
        b: int

    with pytest.raises(
        pydantic.ValidationError,
        match=r"(?s)item\.Child1\.a.*required.*item\.Child2.b.*required",
    ):
        Container(item={"c": 1})


def test_validation_error_good_message_on_disc_union() -> None:
    """The validation error should still be good (discriminated union)"""
    base = _make_discriminated_base()

    class Container(pydantic.BaseModel):
        item: base

    class Child1(base, extra="forbid"):
        a: int

    class Child2(base, extra="forbid"):
        b: int

    with pytest.raises(
        pydantic.ValidationError,
        match=r"(?s)item.*Unable to extract tag using discriminator",
    ):
        Container(item={"c": 1})

    with pytest.raises(
        pydantic.ValidationError, match=r"(?s)item\.Child1\.a.*required"
    ):
        Container(item={"kind": "Child1"})


def test_implicit_recursive_models() -> None:
    """Tests recursive models with an implicit union"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        """Base class, has discriminator value generator"""

    class Base2(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        """Base class, has discriminator value generator"""

    class A(Base):
        """A concrete non-recursive subclass"""

        a: int

    class B(Base):
        """A concrete recursive subclass"""

        b: int
        other: Base

    class C(Base):
        """Recursive subclass"""

        c: Base
        other: Base2

    class D(Base2):
        d: int
        other: Base

    model = D.model_validate_json(
        """
        {
          "name": "D", "d": 1, "other": {
            "name": "B", "b": 2, "other": {
              "name": "C", "c": {"name": "A", "a": 3}, "other": {
                "name": "D", "d": 4, "other": {
                  "name": "A", "a": 5
                }
              }
            }
          }
        }
        """
    )
    assert model == D(d=1, other=B(b=2, other=C(c=A(a=3), other=D(d=4, other=A(a=5)))))
