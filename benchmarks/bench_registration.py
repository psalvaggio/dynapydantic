"""Registration scaling benchmarks."""

import typing as ty

import pydantic
import pytest
from pytest_codspeed.plugin import BenchmarkFixture

from benchmarks.conftest import PARAM_SIZES, make_tracking_group


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_register_existing_registry(benchmark: BenchmarkFixture, size: int) -> None:
    """Time one registration after a registry has already reached N-1 entries."""
    group, _ = make_tracking_group(size - 1)
    model = pydantic.create_model(
        "NewVariant",
        type=(ty.Literal["NewVariant"], "NewVariant"),
        value=(int, 0),
    )
    baseline = dict(group.models)

    def reset(*_args: ty.Any) -> None:
        group.models = dict(baseline)
        group._generation = len(baseline)

    benchmark.pedantic(
        group.register_model,
        args=(model, "NewVariant"),
        setup=reset,
        rounds=10,
    )
