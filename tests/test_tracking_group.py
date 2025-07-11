"""Unit test for TrackingGroup"""

import typing as ty

import pydantic
import pytest

import dynapydantic


def test_tracking_group() -> None:
    """Test basic usage of TrackingGroup"""
    # Make a simple 2 registered model setup
    group = dynapydantic.TrackingGroup(name="Test", discriminator_field="name")

    @group.register()
    class A(pydantic.BaseModel):
        name: ty.Literal["A"] = "A"
        a: int

    @group.register("B")
    class B(pydantic.BaseModel):
        a: int

    # Make sure the models and union look good
    assert group.models == {"A": A, "B": B}
    assert group.union(annotated=False) is ty.Union[A, B]  # noqa: UP007

    annotated_union = group.union()
    assert ty.get_origin(annotated_union) is ty.Annotated
    annotated_args = ty.get_args(annotated_union)
    assert len(annotated_args) == 2
    assert annotated_args[1].discriminator == "name"
    assert ty.get_origin(annotated_args[0]) is ty.Union
    union_args = ty.get_args(annotated_args[0])
    assert union_args[0] == ty.Annotated[A, pydantic.Tag("A")]
    assert union_args[1] == ty.Annotated[B, pydantic.Tag("B")]


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
        field: group.union()

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
