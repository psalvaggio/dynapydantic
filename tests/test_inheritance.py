"""Tests for how dynapydantic propagates to subclasses"""

import typing as ty

import pydantic
import pytest

import dynapydantic
from dynapydantic.version_check import pydantic_lt


def test_inheritance_tree_basic() -> None:
    """Test a somewhat complex inheritance tree"""

    class Base1(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class Base2(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    class MidA(Base1):
        pass

    class MidB(Base1, exclude_from_union=True):
        pass

    class MidC(Base2, exclude_from_union=True):
        pass

    class LeafA(MidA):
        pass

    class LeafB(MidB):
        pass

    class LeafC(MidB, MidC):
        pass

    class LeafD(MidC):
        pass

    # 0:      Base1        Base2
    #        /    \          |
    # 1:  MidA    MidB      MidC
    #      |      /  \     /    \
    # 2: LeafA LeafB  LeafC    LeafD

    # Test layer 0
    assert set(dynapydantic.registered_models(Base1).values()) == {
        MidA,
        LeafA,
        LeafB,
        LeafC,
    }
    assert set(dynapydantic.registered_models(Base2).values()) == {LeafC, LeafD}

    # Test layer 1
    assert set(dynapydantic.registered_models(MidA).values()) == {MidA, LeafA}
    assert set(dynapydantic.registered_models(MidB).values()) == {LeafB, LeafC}
    assert set(dynapydantic.registered_models(MidC).values()) == {LeafC, LeafD}

    # Test layer 2
    assert set(dynapydantic.registered_models(LeafA).values()) == {LeafA}
    assert set(dynapydantic.registered_models(LeafB).values()) == {LeafB}
    assert set(dynapydantic.registered_models(LeafC).values()) == {LeafC}
    assert set(dynapydantic.registered_models(LeafD).values()) == {LeafD}

    for field_t, data, truth in (
        (Base1, {"name": "MidA"}, MidA()),
        (Base1, {"name": "LeafA"}, LeafA()),
        (Base1, {"name": "LeafB"}, LeafB()),
        (Base1, {"name": "LeafC"}, LeafC()),
        (MidA, {"name": "MidA"}, MidA()),
        (MidA, {"name": "LeafA"}, LeafA()),
        (LeafA, {"name": "LeafA"}, LeafA()),
        (MidB, {"name": "LeafB"}, LeafB()),
        (MidB, {"name": "LeafC"}, LeafC()),
        (LeafB, {"name": "LeafB"}, LeafB()),
        (LeafC, {"name": "LeafC"}, LeafC()),
        (Base2, {"name": "LeafC"}, LeafC()),
        (Base2, {"name": "LeafD"}, LeafD()),
        (LeafD, {"name": "LeafD"}, LeafD()),
    ):

        class Model(pydantic.BaseModel):
            f: dynapydantic.Polymorphic[field_t]

        try:
            m = Model(f=data)
        except pydantic.ValidationError as e:
            pytest.fail(f"Failed test ({field_t=}, {data=}, {truth=}):\n{e}")

        assert m.f == truth


def test_changing_union_from_smart_to_discriminated() -> None:
    """Test a subclass changing a union type"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class Mid(Base, exclude_from_union=True):
        pass

    class MidA(
        Mid,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        a: int

    class B(MidA):
        b: int

    class C(MidA):
        c: int

    class Container(pydantic.BaseModel):
        f1: dynapydantic.Polymorphic[Base]
        f2: dynapydantic.Polymorphic[MidA]

    truth: dict[str, ty.Any] = {
        "$defs": {
            "B": {
                "properties": {
                    "a": {"title": "A", "type": "integer"},
                    "b": {"title": "B", "type": "integer"},
                    "name": {
                        "title": "Name",
                        "type": "string",
                        "const": "B",
                        "default": "B",
                    },
                },
                "required": ["a", "b"],
                "title": "B",
                "type": "object",
            },
            "C": {
                "properties": {
                    "a": {"title": "A", "type": "integer"},
                    "c": {"title": "C", "type": "integer"},
                    "name": {
                        "title": "Name",
                        "type": "string",
                        "const": "C",
                        "default": "C",
                    },
                },
                "required": ["a", "c"],
                "title": "C",
                "type": "object",
            },
            "MidA": {
                "properties": {
                    "a": {"title": "A", "type": "integer"},
                    "name": {
                        "title": "Name",
                        "type": "string",
                        "const": "MidA",
                        "default": "MidA",
                    },
                },
                "required": ["a"],
                "title": "MidA",
                "type": "object",
            },
        },
        "properties": {
            "f1": {
                "anyOf": [
                    {"$ref": "#/$defs/MidA"},
                    {"$ref": "#/$defs/B"},
                    {"$ref": "#/$defs/C"},
                ],
                "title": "F1",
            },
            "f2": {
                "discriminator": {
                    "mapping": {
                        "MidA": "#/$defs/MidA",
                        "B": "#/$defs/B",
                        "C": "#/$defs/C",
                    },
                    "propertyName": "name",
                },
                "oneOf": [
                    {"$ref": "#/$defs/MidA"},
                    {"$ref": "#/$defs/B"},
                    {"$ref": "#/$defs/C"},
                ],
                "title": "F2",
            },
        },
        "required": ["f1", "f2"],
        "title": "Container",
        "type": "object",
    }

    # redundant enum removed in: https://github.com/pydantic/pydantic/pull/11321
    if pydantic_lt((2, 10, 0)):
        truth["$defs"]["B"]["properties"]["name"]["enum"] = ["B"]
        truth["$defs"]["C"]["properties"]["name"]["enum"] = ["C"]
        truth["$defs"]["MidA"]["properties"]["name"]["enum"] = ["MidA"]

    assert Container.model_json_schema() == truth
