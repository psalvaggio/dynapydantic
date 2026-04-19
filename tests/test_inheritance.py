"""Tests for how dynapydantic propagates to subclasses"""

import pydantic
import pytest

import dynapydantic


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

    assert Container.model_json_schema() == {
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


# The following tests are testing the guard rails put up on
# implicit_polymorphic. These are there because of an implementation
# limitations. Feel free to revise these test in the future if you figure out
# how to make implicit_polymorphic work like dynapydantic.Polymorphic above. I
# ran into issues because implicit_polymorphic requires overriding
# __get_pydantic_core_schema__ and we want two behaviors out of this. If a
# parent class is requesting the schema, as part of their union we want to
# bypass the override, but if it is used directly as an annotation, we do not.
# I couldn't figure out a way to route these two paths separately. So, I
# decided that implicit_polymorphic should NOT inherit and having two in
# and MRO would be an error.


def test_implicit_polymorphic_only_on_direct_descendents() -> None:
    """implicit_polymorphic is only allowed on direct descendents of STM"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    with pytest.raises(
        dynapydantic.ConfigurationError, match="only allowed on direct descendents"
    ):

        class Derived(Base, implicit_polymorphic=True):
            pass


def test_implicit_polymorphic_inheritance() -> None:
    """implicit_polymorphic should NOT inherit"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        pass

    with pytest.raises(
        dynapydantic.ConfigurationError,
        match=(
            "Models with implicit_polymorphic=True may not have parents that also have"
        ),
    ):

        class MidA(
            Base,
            dynapydantic.SubclassTrackingModel,
            implicit_polymorphic=True,
            exclude_from_union=False,
        ):
            pass


def test_implicit_polymorphic_root_in_union() -> None:
    """Test an implicit_polymorphic=True, exclude_from_union=False model"""
    with pytest.raises(
        dynapydantic.ConfigurationError,
        match=(
            "A model with implicit_polymorphic=True may not set "
            "exclude_from_union=False"
        ),
    ):

        class Base(
            dynapydantic.SubclassTrackingModel,
            discriminator_field="name",
            discriminator_value_generator=lambda cls: cls.__name__,
            implicit_polymorphic=True,
            exclude_from_union=False,
        ):
            a: int
