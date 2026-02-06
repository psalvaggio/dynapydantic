"""A test to cover recursive models with dynapydantic"""

import typing as ty

import dynapydantic


def test_recursive_models_without_discriminator_value_generator() -> None:
    """Tests recursive models without a discriminator value generator"""

    class A(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
    ):
        """Base class, has discriminator value generator"""

    class B(A):
        """A concrete non-recursive subclass"""

        name: ty.Literal["B"] = "B"
        b: int

    class C(A):
        """Recursive subclass"""

        name: ty.Literal["C"] = "C"
        c: dynapydantic.Polymorphic[A]

    for cls in A.registered_subclasses().values():
        cls.model_rebuild(force=True)

    model = C(c=C(c=B(b=1)))
    assert isinstance(model.c, C)
    assert isinstance(model.c.c, B)
    assert model.c.c.b == 1


def test_recursive_models_with_model_value_generator() -> None:
    """Tests recursive models with a discriminator value generator"""

    class A(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        """Base class, has discriminator value generator"""

    class B(A):
        """A concrete non-recursive subclass"""

        b: int

    class C(A):
        """Recursive subclass"""

        c: dynapydantic.Polymorphic[A]

    for cls in A.registered_subclasses().values():
        cls.model_rebuild(force=True)

    model = C(c=C(c=B(b=1)))
    assert isinstance(model.c, C)
    assert isinstance(model.c.c, B)
    assert model.c.c.b == 1
