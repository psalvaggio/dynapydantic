"""Shared fixtures for the dynapydantic benchmarks."""

from __future__ import annotations

import dataclasses
import typing as ty

import pydantic
import pytest

import dynapydantic

PARAM_SIZES = (1, 10, 50, 100, 500)


@dataclasses.dataclass(frozen=True)
class BenchmarkCase:
    """A fully constructed model setup, ready for timing."""

    group: dynapydantic.TrackingGroup
    models: tuple[type[pydantic.BaseModel], ...]
    wrapper: type[pydantic.BaseModel]
    valid_payloads: tuple[dict[str, ty.Any], ...]
    invalid_payloads: tuple[dict[str, ty.Any], ...]


def make_tracking_group(
    size: int,
    *,
    union_mode: str | None = None,
) -> tuple[dynapydantic.TrackingGroup, tuple[type[pydantic.BaseModel], ...]]:
    """Build a group and N concrete models before benchmark timing starts."""
    group_kwargs: dict[str, ty.Any] = {"name": f"bench-{size}"}
    if union_mode in (None, "discriminated"):
        group_kwargs.update(
            discriminator_field="type",
            discriminator_value_generator=lambda cls: cls.__name__,
        )
    else:
        group_kwargs["union_mode"] = union_mode
    group = dynapydantic.TrackingGroup(**group_kwargs)

    models = []
    for index in range(size):
        name = f"Variant{index}"
        fields: dict[str, tuple[ty.Any, ty.Any]]
        if union_mode in (None, "discriminated"):
            fields = {
                "type": (ty.Literal[name], name),  # type: ignore[invalid-literal]
                "value": (int, index),
            }
        else:
            fields = {f"value_{index}": (int, index)}
        model = pydantic.create_model(name, **fields)  # type: ignore[no-matching-overload]
        group.register_model(model)
        models.append(model)

    return group, tuple(models)


def make_payloads(
    models: tuple[type[pydantic.BaseModel], ...],
    *,
    union_mode: str | None = None,
) -> tuple[tuple[dict[str, ty.Any], ...], tuple[dict[str, ty.Any], ...]]:
    """Create valid one-per-model payloads and payloads guaranteed to fail."""
    if union_mode in (None, "discriminated"):
        valid = tuple(
            {"type": model.__name__, "value": i} for i, model in enumerate(models)
        )
    else:
        valid = tuple({f"value_{i}": i} for i, _ in enumerate(models))
    if union_mode in (None, "discriminated"):
        invalid = tuple(
            {"type": "MissingVariant", "value": i} for i in range(len(models))
        )
    else:
        invalid_payload = {
            f"value_{index}": "not-an-integer" for index in range(len(models))
        }
        invalid = tuple(invalid_payload.copy() for _ in models)
    return valid, invalid


def validate_invalid(
    wrapper: type[pydantic.BaseModel], payload: dict[str, ty.Any]
) -> None:
    """Run an expected-failure validation without timing exception setup."""
    try:
        wrapper.model_validate(payload)
    except pydantic.ValidationError:
        return
    raise AssertionError


@pytest.fixture
def tracking_case(request: pytest.FixtureRequest) -> BenchmarkCase:
    """Return the standard discriminated setup for a requested size."""
    size = int(
        request.param
        if hasattr(request, "param")
        else request.node.callspec.params["size"]
    )
    group, models = make_tracking_group(size)
    valid, invalid = make_payloads(models)

    class Wrapper(pydantic.BaseModel):
        value: dynapydantic.Union[group]

    return BenchmarkCase(group, models, Wrapper, valid, invalid)


@pytest.fixture
def mode_case(request: pytest.FixtureRequest) -> BenchmarkCase:
    """Return a representative setup for one of Pydantic's union modes."""
    mode = request.node.callspec.params["union_mode"]
    setup_mode = None if mode == "discriminated" else mode
    group, models = make_tracking_group(50, union_mode=setup_mode)
    valid, invalid = make_payloads(models, union_mode=setup_mode)

    class Wrapper(pydantic.BaseModel):
        value: dynapydantic.Union[group]

    return BenchmarkCase(group, models, Wrapper, valid, invalid)
