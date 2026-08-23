"""Serialization scaling benchmarks."""

import pytest

from benchmarks.conftest import PARAM_SIZES, BenchmarkCase


@pytest.fixture
def instances(tracking_case: BenchmarkCase) -> tuple:
    """Build instances outside the timed serialization operation."""
    return tuple(
        tracking_case.wrapper.model_validate({"value": payload})
        for payload in tracking_case.valid_payloads
    )


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_model_dump(benchmark, instances, size: int) -> None:
    """Dump all N variants to Python objects."""
    benchmark(lambda: [instance.model_dump() for instance in instances])


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_model_dump_json(benchmark, instances, size: int) -> None:
    """Dump all N variants to JSON."""
    benchmark(lambda: [instance.model_dump_json() for instance in instances])
