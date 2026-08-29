"""Compare dynapydantic with an equivalent hand-written discriminated union.

These are the most direct benchmarks for estimating per-operation library
overhead.  Model creation, subclass registration, union creation, and schema
compilation all happen in ``_setups`` and are deliberately excluded from the
timed call.  The reported validation ratio is therefore approximately
``dynamic validation time / manual validation time``; subtracting one and
multiplying by 100 gives the percentage overhead.  The same interpretation
applies to serialization.

Both variants use Pydantic models and a discriminator, and the payload selects
the last of ``N`` variants.  This measures the cost of using dynapydantic's
polymorphic field at steady state, not the cost of maintaining the registry or
discovering plugins.  Compare the curves as ``N`` grows rather than treating a
single absolute time as universal: Pydantic and Python versions, hardware,
and model shape all affect the baseline.
"""

from __future__ import annotations

import functools
import operator
import typing as ty

import pydantic
import pytest

import dynapydantic

if ty.TYPE_CHECKING:
    from pytest_codspeed.plugin import BenchmarkFixture


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
@pytest.mark.benchmark(group="validation")
def test_validation(benchmark: BenchmarkFixture, size: int) -> None:
    """Time steady-state dynapydantic validation for the last variant.

    Compare this result with :func:`test_validation_manual` at the same
    ``size``.  A result of 1.20x means dynapydantic took about 20% longer;
    it does not mean 20 percentage points of application latency.
    """
    _, dynamic, _, payload = _setups(size)
    benchmark(dynamic.model_validate, payload)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
@pytest.mark.benchmark(group="validation")
def test_validation_manual(benchmark: BenchmarkFixture, size: int) -> None:
    """Time the hand-written discriminated-union validation baseline.

    This is the denominator for the validation overhead ratio.  Setup and
    schema compilation are intentionally outside the benchmark, so this does
    not answer how much registration or startup costs.
    """
    manual, _, payload, _ = _setups(size)
    benchmark(manual.model_validate, payload)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
@pytest.mark.benchmark(group="serialization")
def test_serialization(benchmark: BenchmarkFixture, size: int) -> None:
    """Time steady-state serialization of a dynapydantic instance.

    The instance is validated before timing.  Compare with
    :func:`test_serialization_manual` to estimate serialization overhead only;
    validation and model construction are not included.
    """
    _, dynamic, _, payload = _setups(size)
    instance = dynamic.model_validate(payload)
    benchmark(instance.model_dump)


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
@pytest.mark.benchmark(group="serialization")
def test_serialization_manual(benchmark: BenchmarkFixture, size: int) -> None:
    """Time serialization of the equivalent manual-union instance.

    Use this as the denominator for the serialization overhead ratio at the
    same registry size.
    """
    manual, _, payload, _ = _setups(size)
    instance = manual.model_validate(payload)
    benchmark(instance.model_dump)
