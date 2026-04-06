"""Unit test for TrackingGroup"""

import typing as ty
from unittest import mock

import pydantic
import pytest

import dynapydantic


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"discriminator_field": "name"}, id="inline-field-kwarg"),
        pytest.param(
            {"union_mode": {"discriminator_field": "name"}},
            id="union-mode-dict",
        ),
        pytest.param(
            {
                "union_mode": dynapydantic.DiscriminatedConfig(
                    discriminator_field="name",
                ),
            },
            id="union-mode-model",
        ),
    ],
)
def test_simple_disrciminated_tracking_group(kwargs: dict[str, ty.Any]) -> None:
    """Test basic usage of TrackingGroup to make a discriminated union"""
    # Make a simple 2 registered model setup
    group = dynapydantic.TrackingGroup(name="Test", **kwargs)

    @group.register()
    class A(pydantic.BaseModel):
        name: ty.Literal["A"] = "A"
        a: int

    @group.register("B")
    class B(pydantic.BaseModel):
        a: int

    # Make sure the models and union look good
    assert group.models == {"A": A, "B": B}
    assert group.union(plain=True) == (A | B)
    with pytest.warns(DeprecationWarning, match="annotated"):
        assert group.union(annotated=False) == (A | B)

    annotated_union = group.union()
    assert ty.get_origin(annotated_union) is ty.Annotated
    annotated_args = ty.get_args(annotated_union)
    assert len(annotated_args) == 2
    assert annotated_args[0] == (
        ty.Annotated[A, pydantic.Tag("A")] | ty.Annotated[B, pydantic.Tag("B")]
    )
    assert annotated_args[1].discriminator == "name"


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        pytest.param(
            {}, "Either union_mode or discriminator_field must be given", id="no-args"
        ),
        pytest.param(
            {
                "discriminator_field": "foo",
                "union_mode": {"discriminator_field": "foo"},
            },
            "Received both union_mode and discriminator_field; pass one or the other.",
            id="redundant-args",
        ),
    ],
)
def test_bad_construction(kwargs: dict[str, ty.Any], match: str) -> None:
    """Test bad construction of a tracking group"""
    with pytest.raises(pydantic.ValidationError, match=match):
        dynapydantic.TrackingGroup(name="test", **kwargs)


def test_invalid_type() -> None:
    """Test that we don't construct from garbage input"""
    with pytest.raises(pydantic.ValidationError, match="model_type"):
        dynapydantic.TrackingGroup.model_validate("foo")


def test_model_validate_noop() -> None:
    """Test that a tracking group can be copied"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")
    assert group.union_mode == dynapydantic.DiscriminatedConfig(
        discriminator_field="name", discriminator_value_generator=None
    )
    assert group.discriminator_field == "name"
    assert group.discriminator_value_generator is None

    group2 = dynapydantic.TrackingGroup.model_validate(group)
    assert group2 is group
    assert group2.union_mode == dynapydantic.DiscriminatedConfig(
        discriminator_field="name", discriminator_value_generator=None
    )
    assert group2.discriminator_field == "name"
    assert group2.discriminator_value_generator is None


def test_smart_union_mode() -> None:
    """Test making a tracking group with the "smart" union"""
    group = dynapydantic.TrackingGroup(name="Test", union_mode="smart")

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    class B(pydantic.BaseModel):
        a: int
        b: int

    group.register_model(B)

    with pytest.warns(match="The value will be ignored"):

        @group.register("C")
        class C(pydantic.BaseModel):
            c: int

    assert group.union() == A | B | C
    assert group.union(plain=True) == A | B | C
    with pytest.warns(DeprecationWarning, match="annotated"):
        assert group.union(annotated=False) == A | B | C

    assert pydantic.TypeAdapter(group.union()).validate_python({"a": 1, "b": 5}) == B(
        a=1, b=5
    )


def test_left_to_right_union_mode() -> None:
    """Test a left-to-right union"""
    group = dynapydantic.TrackingGroup(name="Test", union_mode="left_to_right")

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    @group.register()
    class B(pydantic.BaseModel):
        a: int
        b: int | None = None

    u = group.union()
    assert ty.get_origin(u) is ty.Annotated
    args = ty.get_args(u)
    assert args[0] == A | B

    assert pydantic.TypeAdapter(group.union()).validate_python({"a": 1, "b": 5}) == A(
        a=1
    )


def test_ensure_union_mode() -> None:
    """Test that there is a guard against no union_mode"""

    class MyTrackingGroup(dynapydantic.TrackingGroup):
        @pydantic.model_validator(mode="before")
        @classmethod
        def _coerce_union_mode(cls, data: ty.Any) -> ty.Any:  # noqa: ANN401
            if isinstance(data, dict):
                data.pop("union_mode", None)
                data.pop("discriminator_field", None)
            return data

    with pytest.raises(pydantic.ValidationError, match="union_mode is required"):
        MyTrackingGroup(name="test", union_mode="smart")


def test_no_default_val() -> None:
    """Test that an error is raised when no default discriminator value is given"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    with pytest.raises(dynapydantic.RegistrationError, match="no default value"):

        @group.register()
        class A(pydantic.BaseModel):
            name: ty.Literal["A"]


def test_duplicate_discriminators() -> None:
    """Registering different subclasses under the same identifier is an error"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    @group.register("A")
    class A(pydantic.BaseModel):
        pass

    group.register_model(A)  # this is fine to register the same class twice

    with pytest.raises(dynapydantic.RegistrationError, match="already in use"):

        @group.register("A")
        class B(pydantic.BaseModel):
            pass


def test_non_str_discriminator_is_an_error() -> None:
    """Discriminators must be strings"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    class A(pydantic.BaseModel):
        pass

    with pytest.raises(
        dynapydantic.RegistrationError,
        match="discriminator_value must be a str if given, was int",
    ):
        group.register_model(A, 5)  # type: ignore[bad-argument-type]

    with pytest.raises(
        dynapydantic.RegistrationError,
        match=r"B.name had a default value of 14, which was of type int, not str",
    ):

        @group.register
        class B(pydantic.BaseModel):
            name: ty.Literal[14] = 14

    with pytest.raises(
        dynapydantic.RegistrationError,
        match="discriminator_value must be a str if given, was float",
    ):

        @group.register(1.23)  # type: ignore[bad-argument-type]
        class C(pydantic.BaseModel):
            pass


def test_duplicate_models_no_discriminated() -> None:
    """Test the super pessimistic guard in plain registration"""
    group = dynapydantic.TrackingGroup(name="Test", union_mode="smart")

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    class B(pydantic.BaseModel):
        b: int

    with (
        mock.patch("builtins.id", return_value=id(A)),
        pytest.raises(
            dynapydantic.RegistrationError,
            match=(
                r'Cannot register .*B under the ".*" identifier, which is '
                r"already in use by .*A"
            ),
        ),
    ):
        group.register_model(B)


def test_no_discriminator() -> None:
    """Test cases where no discriminator is provided"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    class A(pydantic.BaseModel):
        a: int

    with pytest.raises(
        dynapydantic.RegistrationError,
        match="unable to determine a discriminator value",
    ):
        group.register_model(A)

    with pytest.raises(
        dynapydantic.RegistrationError,
        match="unable to determine a discriminator value",
    ):

        @group.register()
        class B(pydantic.BaseModel):
            b: int


def test_discriminator_injection_from_register() -> None:
    """Test that register() can inject the discriminator field"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="type")

    @group.register("A")
    class A(pydantic.BaseModel):
        a: int

    assert "type" in A.model_fields
    assert "a" in A.model_fields

    assert A(a=1).model_dump() == {"type": "A", "a": 1}


def test_discriminator_injection_from_generator() -> None:
    """Test that the discriminator_value_generator can inject the field"""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    @group.register("B1")  # this should take priority
    class B(pydantic.BaseModel):
        a: int

    @group.register()
    class C(pydantic.BaseModel):
        name: ty.Literal["C1"] = "C1"  # this should take priority
        a: int

    class D(pydantic.BaseModel):
        a: int

    group.register_model(D)

    class E(pydantic.BaseModel):
        name: ty.Literal["E1"] = "E1"  # this should take priority
        a: int

    group.register_model(E)

    assert group.models == {"A": A, "B1": B, "C1": C, "D": D, "E1": E}


def test_register_with_manual_field_raises() -> None:
    """Test that an ambiguous register call fails"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    with pytest.raises(dynapydantic.AmbiguousDiscriminatorValueError):

        @group.register("B")
        class A(pydantic.BaseModel):
            name: ty.Literal["A"] = "A"


def test_that_the_union_works() -> None:
    """Test that the union actually works as a pydantic annotation"""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="type",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    @group.register()
    class B(pydantic.BaseModel):
        a: int

    class UserModel(pydantic.BaseModel):
        field: group.union()  # pyrefly: ignore

    assert UserModel(field={"type": "A", "a": 5}).field == A(a=5)
    assert UserModel(field={"type": "B", "a": 5}).field == B(a=5)

    # Make sure only the right model is tried in validation
    with pytest.raises(pydantic.ValidationError) as exc_info:
        UserModel(field={"type": "B"})

    assert exc_info.value.error_count() == 1
    assert exc_info.value.errors()[0]["loc"] == ("field", "B", "a")


def test_that_load_plugins_doesnt_raise_on_no_entrypoint() -> None:
    """load_plugins() should be a noop in this case"""
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="type")
    group.load_plugins()


def test_tracking_group_models_default_is_not_shared() -> None:
    """Each TrackingGroup should have its own independent models dict."""
    g1 = dynapydantic.TrackingGroup(name="G1", discriminator_field="t")
    g2 = dynapydantic.TrackingGroup(name="G2", discriminator_field="t")

    @g1.register("A")
    class A(pydantic.BaseModel):
        pass

    assert "A" not in g2.models, "g2.models should be independent from g1.models"


def test_registering_same_class_twice_is_idempotent() -> None:
    """Registering the same class twice should not raise or duplicate."""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    group.register_model(A)  # second time
    group.register_model(A)  # third time

    assert list(group.models.values()) == [A]


def test_register_model_with_manual_field_ignores_generator() -> None:
    """register_model uses the field default even if generator would differ."""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="name",
        discriminator_value_generator=lambda cls: "GENERATED",
    )

    class A(pydantic.BaseModel):
        name: ty.Literal["MANUAL"] = "MANUAL"
        a: int

    group.register_model(A)

    # The field default wins; generator is only called when field is absent
    assert "MANUAL" in group.models
    assert "GENERATED" not in group.models


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
    group = dynapydantic.TrackingGroup(name="Test", **kwargs)

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    assert group.union() is A


def test_union_with_no_registered_models_raises() -> None:
    """union() with no registered models should raise a clear library error."""
    group = dynapydantic.TrackingGroup(name="Empty", discriminator_field="t")
    with pytest.raises(dynapydantic.NoRegisteredTypesError):
        group.union()


def test_discriminator_injection_into_frozen_model() -> None:
    """Injecting a discriminator field into a frozen model should work"""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="type",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register()
    class A(pydantic.BaseModel, frozen=True):
        a: int

    instance = A(a=1)
    assert instance.model_dump()["type"] == "A"


def test_register_non_pydantic_class_raises() -> None:
    """Registering a plain Python class should fail gracefully."""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="kind",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    with pytest.raises(dynapydantic.RegistrationError):

        @group.register()
        class Oops:  # not a BaseModel
            pass

    with pytest.raises(dynapydantic.RegistrationError):
        group.register_model(5)  # type: ignore[bad-argument-type]

    with pytest.raises(dynapydantic.RegistrationError):
        group.register_model(int)  # type: ignore[bad-argument-type]


def test_round_trip_with_round_trip_flag() -> None:
    """model_dump(round_trip=True) followed by model_validate should work."""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="type",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register()
    class A(pydantic.BaseModel):
        a: int

    @group.register()
    class B(pydantic.BaseModel):
        b: int

    class Outer(pydantic.BaseModel):
        val: group.union()  # type: ignore[not-a-type]

    m = Outer(val={"type": "A", "a": 3})
    raw = m.model_dump(round_trip=True)
    assert Outer.model_validate(raw) == m


def test_register_without_parentheses_works() -> None:
    """Using @group.register instead of @group.register() should raise a good error"""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    @group.register
    class A(pydantic.BaseModel):
        a: int

    @group.register()
    class B(pydantic.BaseModel):
        b: int

    assert group.models == {"A": A, "B": B}


def test_generator_that_raises_propagates_cleanly() -> None:
    """An exception from the generator should propagate without wrapping."""

    def bad_gen(cls: type) -> str:
        msg = "generator exploded"
        raise ValueError(msg)

    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="tag",
        discriminator_value_generator=bad_gen,
    )
    with pytest.raises(ValueError, match="generator exploded"):

        @group.register
        class A(pydantic.BaseModel):
            a: int


def test_field_clobbering_not_allowed() -> None:
    """Test that discriminator field injection clobbering is an error"""
    group = dynapydantic.TrackingGroup(
        name="Test",
        discriminator_field="name",
        discriminator_value_generator=lambda cls: cls.__name__,
    )

    class A(pydantic.BaseModel):
        name: ty.ClassVar[str] = "A"
        x: int
        y: int

    with pytest.raises(
        dynapydantic.RegistrationError,
        match=(
            r'Cannot inject discriminator field "name" into A: an attribute '
            "with that name already exists. Rename either the attribute or the "
            "discriminator_field to avoid the conflict."
        ),
    ):
        group.register_model(A)

    @group.register
    class B(pydantic.BaseModel):
        name: ty.Literal["B"] = "B"  # consistent and fine
        key: str

    class C(pydantic.BaseModel):
        name: str = "C"  # has a default str value, but it's not a Literal
        key: str

    with pytest.raises(
        dynapydantic.RegistrationError,
        match=(
            r'the discriminator field "name" already existed in C, but '
            r"its type annotation was <class 'str'>, not Literal\."
        ),
    ):
        group.register_model(C)
