"""Validation and error-path comparisons for all supported union modes."""

import pytest

from benchmarks.conftest import validate_invalid


@pytest.mark.parametrize("union_mode", ["discriminated", "smart", "left_to_right"])
def test_mode_valid(benchmark, mode_case, union_mode: str) -> None:
    """Validate a representative payload under each union mode."""
    payload = mode_case.valid_payloads[-1]
    benchmark(mode_case.wrapper.model_validate, {"value": payload})


@pytest.mark.parametrize("union_mode", ["discriminated", "smart", "left_to_right"])
def test_mode_invalid(benchmark, mode_case, union_mode: str) -> None:
    """Measure the error path under each union mode."""
    payload = {"value": mode_case.invalid_payloads[0]}
    benchmark(validate_invalid, mode_case.wrapper, payload)
