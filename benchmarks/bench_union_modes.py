"""Validation and error-path comparisons for all supported union modes.

The setup contains 50 variants and is excluded from timing.  These results
describe Pydantic's union search strategy once a union already exists, not
dynapydantic's registry-management overhead.  Valid payloads select the last
variant, making the work of ordered/non-discriminated modes visible; invalid
payloads exercise their full error path and should be compared separately
from successful validation.
"""

import pytest
from pytest_codspeed.plugin import BenchmarkFixture

from benchmarks.conftest import validate_invalid


@pytest.mark.parametrize("union_mode", ["discriminated", "smart", "left_to_right"])
def test_mode_valid(benchmark: BenchmarkFixture, mode_case, union_mode: str) -> None:
    """Time successful validation under one Pydantic union mode.

    Compare modes at the same variant count.  Discriminated validation should
    generally be close to constant with respect to union size, while smart
    and left-to-right modes may inspect several candidates before the last
    variant matches.
    """
    payload = mode_case.valid_payloads[-1]
    benchmark(mode_case.wrapper.model_validate, {"value": payload})


@pytest.mark.parametrize("union_mode", ["discriminated", "smart", "left_to_right"])
def test_mode_invalid(benchmark: BenchmarkFixture, mode_case, union_mode: str) -> None:
    """Time expected-failure validation under one union mode.

    Exception handling is outside the timed helper; Pydantic's construction
    of the validation error remains part of the measured failure path.
    """
    payload = {"value": mode_case.invalid_payloads[0]}
    benchmark(validate_invalid, mode_case.wrapper, payload)
