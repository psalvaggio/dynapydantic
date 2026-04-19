"""Tests for how dynapydantic propagates to subclasses"""

import pydantic

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

        assert Model(f=data).f == truth
