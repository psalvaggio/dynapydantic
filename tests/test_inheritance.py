"""Tests for how dynapydantic propagates to subclasses"""

import dynapydantic


def test_inheritance_tree_basic() -> None:
    """Test a somewhat complex inheritance tree"""

    class Base1(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        pass

    class Base2(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
        implicit_polymorphic=True,
    ):
        pass

    class LeafA(Base1):
        a: int

    class MidA(Base1, exclude_from_union=True):
        pass

    class MidB(Base2, exclude_from_union=True):
        pass

    class LeafB(LeafA):
        pass

    class LeafC(MidA):
        pass

    class LeafD(MidA, MidB):
        pass

    class LeafE(MidB):
        pass

    # 0:      Base1        Base2
    #        /    \          |
    # 1: LeafA    MidA      MidB
    #      |      /  \     /    \
    # 2: LeafB LeafC  LeafD    LeafE

    # Test layer 0
    assert set(dynapydantic.registered_models(Base1).values()) == {
        LeafA,
        LeafB,
        LeafC,
        LeafD,
    }
    assert set(dynapydantic.registered_models(Base2).values()) == {LeafD, LeafE}

    # Test layer 1
    assert set(dynapydantic.registered_models(LeafA).values()) == {LeafA, LeafB}
    assert set(dynapydantic.registered_models(MidA).values()) == {LeafC, LeafD}
    assert set(dynapydantic.registered_models(MidB).values()) == {LeafD, LeafE}

    # Test layer 2
    assert set(dynapydantic.registered_models(LeafB).values()) == {LeafB}
    assert set(dynapydantic.registered_models(LeafC).values()) == {LeafC}
    assert set(dynapydantic.registered_models(LeafD).values()) == {LeafD}
    assert set(dynapydantic.registered_models(LeafE).values()) == {LeafE}
