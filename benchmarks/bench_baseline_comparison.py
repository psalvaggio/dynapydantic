"""Compare dynapydantic with a hand-written discriminated union."""

from __future__ import annotations

import functools
import operator
import typing as ty

import pydantic
import pytest

import dynapydantic

if ty.TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


def _setups(
    size: int,
) -> tuple[
    type[pydantic.BaseModel],
    type[pydantic.BaseModel],
    dict[str, ty.Any],
    dict[str, ty.Any],
]:
    """Build equivalent manual and dynamic models outside benchmark timing."""
    manual_models = tuple(
        pydantic.create_model(
            f"Manual{index}",
            type=(
                ty.Literal[f"Variant{index}"],  # type: ignore[invalid-literal]
                f"Variant{index}",
            ),
            value=(int, index),
        )
        for index in range(size)
    )
    manual_union = functools.reduce(operator.or_, manual_models)

    class Manual(pydantic.BaseModel):
        value: ty.Annotated[manual_union, pydantic.Field(discriminator="type")]

    class Dynamic(
        dynapydantic.SubclassTrackingModel,
        discriminator_field="type",
        discriminator_value_generator=lambda cls: cls.__name__,
    ):
        pass

    pydantic.create_model(
        "DynamicVariant0",
        __base__=Dynamic,
        value=(int, 0),
    )
    for index in range(1, size):
        pydantic.create_model(
            f"DynamicVariant{index}", __base__=Dynamic, value=(int, index)
        )

    class DynModel(pydantic.BaseModel):
        value: dynapydantic.Polymorphic[Dynamic]

    payload = {"value": {"type": f"DynamicVariant{size - 1}", "value": size - 1}}
    manual_payload = {"value": {"type": f"Variant{size - 1}", "value": size - 1}}
    return Manual, DynModel, manual_payload, payload


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
def test_validation(benchmark: BenchmarkFixture, size: int) -> None:
    """Compare validation of equivalent last-variant payloads."""
    _, dynamic, _, payload = _setups(size)
    benchmark.group = "validation"
    benchmark(dynamic.model_validate, payload)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
def test_validation_manual(benchmark: BenchmarkFixture, size: int) -> None:
    """Manual-union counterpart to dynamic validation."""
    manual, _, payload, _ = _setups(size)
    benchmark.group = "validation"
    benchmark(manual.model_validate, payload)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
def test_serialization(benchmark: BenchmarkFixture, size: int) -> None:
    """Compare serialization of equivalent validated instances."""
    _, dynamic, _, payload = _setups(size)
    instance = dynamic.model_validate(payload)
    benchmark.group = "serialization"
    benchmark(instance.model_dump)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
def test_serialization_manual(benchmark: BenchmarkFixture, size: int) -> None:
    """Manual-union counterpart to dynamic serialization."""
    manual, _, payload, _ = _setups(size)
    instance = manual.model_validate(payload)
    benchmark.group = "serialization"
    benchmark(instance.model_dump)
