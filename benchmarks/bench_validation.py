"""Validation scaling benchmarks."""

import pytest
from pytest_codspeed.plugin import BenchmarkFixture

from benchmarks.conftest import PARAM_SIZES, validate_invalid


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_validate_first(benchmark: BenchmarkFixture, tracking_case, size: int) -> None:
    """Validate the first registered payload."""
    benchmark(
        tracking_case.wrapper.model_validate, {"value": tracking_case.valid_payloads[0]}
    )


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_validate_last(benchmark: BenchmarkFixture, tracking_case, size: int) -> None:
    """Validate the last registered payload."""
    benchmark(
        tracking_case.wrapper.model_validate,
        {"value": tracking_case.valid_payloads[-1]},
    )


@pytest.mark.parametrize("size", PARAM_SIZES)
def test_validate_invalid(
    benchmark: BenchmarkFixture, tracking_case, size: int
) -> None:
    """Validate a payload with an unknown discriminator."""
    payload = {"value": tracking_case.invalid_payloads[0]}
    benchmark(validate_invalid, tracking_case.wrapper, payload)
