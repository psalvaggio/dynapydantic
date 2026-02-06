"""Unit test for Polymorphic"""

import json

import pydantic

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
