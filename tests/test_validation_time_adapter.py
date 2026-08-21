"""Test behavior of the ValidationTimeAdapter."""

import typing as ty
from pathlib import Path

import pydantic
import pytest

import dynapydantic
from dynapydantic.version_check import pydantic_le, pydantic_lt


def test_validation_time_union_no_members() -> None:
    """An error is raised at validation time when no subclasses exist."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[Base]

    with pytest.raises(
        pydantic.ValidationError,
        match=r"(?s)field.*Unable to produce a union.*dynapydantic_error",
    ):
        Model(field={"some": "dummy value"})


def test_validation_time_realization_inherits() -> None:
    """Validation-time unions work through an inheritance tree."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
        extra="forbid",
    ):
        pass

    class A(Base):
        a: int

    class Mid(Base):
        b: int

    class C(Mid):
        c: int
        other: dynapydantic.Polymorphic[Mid] | None = None

    class D(Mid):
        d: int

    for cls, opts in (
        (Base, {A, Mid, C, D}),
        (A, {A}),
        (Mid, {Mid, C, D}),
        (C, {C}),
        (D, {D}),
    ):
        assert (
            cls.__DYNAPYDANTIC_STM_CONFIG__.union_realization
            == dynapydantic.UnionRealization.VALIDATION
        )
        assert set(dynapydantic.registered_models(cls).values()) == opts

    for field_t, data, truth in (
        (Base, {"a": 1}, A(a=1)),
        (Base, {"b": 1}, Mid(b=1)),
        (Base, {"b": 1, "c": 2}, C(b=1, c=2)),
        (Base, {"b": 1, "d": 2}, D(b=1, d=2)),
        (A, {"a": 1}, A(a=1)),
        (Mid, {"b": 1}, Mid(b=1)),
        (Mid, {"b": 1, "c": 2}, C(b=1, c=2)),
        (Mid, {"b": 1, "d": 2}, D(b=1, d=2)),
        (C, {"b": 1, "c": 2}, C(b=1, c=2)),
        (D, {"b": 1, "d": 2}, D(b=1, d=2)),
        (
            Mid,
            {"b": 1, "c": 2, "other": {"b": 3, "d": 4}},
            C(b=1, c=2, other=D(b=3, d=4)),
        ),
    ):

        class Model(pydantic.BaseModel):
            f: dynapydantic.Polymorphic[field_t]

        assert Model(f=data).f == truth


def test_validation_time_adapter_forwards_context() -> None:
    """Validation context reaches validators on the realized subclass."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Child(Base):
        value: int

        @pydantic.field_validator("value")
        @classmethod
        def validate_value(cls, value: int, info: pydantic.ValidationInfo) -> int:
            if info.context is None:
                return value
            return value + ty.cast("dict[str, int]", info.context)["offset"]

    class Model(pydantic.BaseModel):
        value: dynapydantic.Polymorphic[Base]

    assert Model.model_validate(
        {"value": {"value": 2}}, context={"offset": 3}
    ).value == Child(value=5)


@pytest.mark.parametrize(
    ("model_cfg", "data", "error_match"),
    [
        pytest.param(
            {"strict": True},
            {"value": {"value": "2"}},
            "value",
            id="strict",
        ),
        pytest.param(
            {"extra": "forbid"},
            {"value": {"value": 2, "unexpected": True}},
            "unexpected",
            marks=[
                pytest.mark.xfail(
                    pydantic_le((2, 12, 0)),
                    reason="TypeAdapter's didn't gain support for extra until 2.12",
                )
            ],
            id="extra",
        ),
    ],
)
def test_validation_time_adapter_forwards_model_config(
    model_cfg: dict[str, ty.Any],
    data: dict[str, ty.Any],
    error_match: str,
) -> None:
    """Selected outer-model config is honored by the dynamic adapter."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Child(Base):
        value: int

    class Model(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(**model_cfg)
        value: dynapydantic.Polymorphic[Base]

    with pytest.raises(pydantic.ValidationError, match=error_match):
        Model.model_validate(data)


def test_validation_time_adapter_forwards_from_attributes() -> None:
    """The outer model's from-attributes setting reaches the adapter."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Child(Base):
        value: int

    class Input:
        value = 7

    class Model(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(from_attributes=True)
        value: dynapydantic.Polymorphic[Base]

    assert Model.model_validate({"value": Input()}).value == Child(value=7)


@pytest.mark.xfail(
    pydantic_lt((2, 11, 0)),
    reason="TypeAdapter's didn't support alias config before 2.11.0",
)
def test_validation_time_adapter_forwards_alias_configuration() -> None:
    """Alias and field-name settings reach the realized subclass."""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class Child(Base):
        inner: int = pydantic.Field(validation_alias="raw_value")

    class Model(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(
            validate_by_alias=False,
            validate_by_name=True,
        )
        outer: dynapydantic.Polymorphic[Base]

    assert Model.model_validate({"outer": {"inner": 7}}).outer == Child(raw_value=7)
    with pytest.raises(pydantic.ValidationError, match="raw_value"):
        Model.model_validate({"outer": {"raw_value": 7}})


def test_validation_time_adapter_strict_json_validation() -> None:
    """Test type coercions for a strict model through JSON"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="kind",
        union_realization="validation",
        strict=True,
    ):
        value: int

    class Child(Base):
        kind: ty.Literal["child"] = "child"
        file_path: Path | None = None

    class Model(pydantic.BaseModel, strict=True):
        data: dynapydantic.Polymorphic[Base]

    # Easy path, should not raise
    model = Model(data=Child(value=1, file_path=Path("/foo/bar")))

    json_str = model.model_dump_json(round_trip=True)
    model_rt = Model.model_validate_json(json_str)
    assert model == model_rt


def test_validation_time_adapter_runtime_strict_json_validation() -> None:
    """Test type coercions for a strict model through JSON (runtime)"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="kind",
        union_realization="validation",
    ):
        value: int

    class Child(Base):
        kind: ty.Literal["child"] = "child"
        file_path: Path | None = None

    class Model(pydantic.BaseModel):
        data: dynapydantic.Polymorphic[Base]

    # Easy path, should not raise
    model = Model(data=Child(value=1, file_path=Path("/foo/bar")))

    json_str = model.model_dump_json(round_trip=True)
    model_rt = Model.model_validate_json(json_str, strict=True)
    assert model == model_rt

    with pytest.raises(pydantic.ValidationError, match="value"):
        Model.model_validate_json('{"data": {"value": "1"}}', strict=True)
