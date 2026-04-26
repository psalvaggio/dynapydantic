"""A test to cover recursive models with dynapydantic"""

import typing as ty

import pytest

import dynapydantic


@pytest.mark.parametrize(
    "realization_time",
    ["model-construction", "validation"],
)
def test_recursive_models_without_discriminator_value_generator(
    realization_time: str,
) -> None:
    """Tests recursive models without a discriminator value generator"""

    class A(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="name",
        union_realization=realization_time,
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

    if realization_time != "validation":
        for cls in dynapydantic.registered_models(A).values():
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

    for cls in dynapydantic.registered_models(A).values():
        cls.model_rebuild(force=True)

    model = C(c=C(c=B(b=1)))
    assert isinstance(model.c, C)
    assert isinstance(model.c.c, B)
    assert model.c.c.b == 1


def test_pure_recursive_smart_union_validation_time() -> None:
    """Recursive subclasses using smart union and validation-time union"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class A(Base):
        a: int
        other: dynapydantic.Polymorphic[Base] | None = None

    class B(Base):
        b: int
        other: dynapydantic.Polymorphic[Base] | None = None

    model = A.model_validate_json(
        '{"a": 1, "other": {"b": 2, "other": {"a": 3}}}',
    )
    assert model == A(a=1, other=B(b=2, other=A(a=3)))


def test_pure_recursive_smart_union_model_contruction_time() -> None:
    """Recursive subclasses using smart union and construction-time union"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
    ):
        pass

    class A(Base):
        a: int
        other: "BaseUnion | None" = None

    class B(Base):
        b: int
        other: "BaseUnion | None" = None

    BaseUnion = dynapydantic.Polymorphic[Base]  # noqa: N806
    assert BaseUnion is not None  # silencing an unused variable warning

    for cls in Base.__subclasses__():
        cls.model_rebuild(force=True)

    model = A.model_validate_json(
        '{"a": 1, "other": {"b": 2, "other": {"a": 3}}}',
    )
    assert model == A(a=1, other=B(b=2, other=A(a=3)))
