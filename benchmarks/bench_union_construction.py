"""Union construction scaling benchmarks."""

import pytest

from benchmarks.conftest import PARAM_SIZES


@pytest.mark.parametrize(
    ("tracking_case", "size"),
    [(size, size) for size in PARAM_SIZES],
    indirect=["tracking_case"],
)
def test_union_construction(benchmark, tracking_case, size: int) -> None:
    """Time constructing a union from a registry of N models."""
    benchmark(tracking_case.group.union)
