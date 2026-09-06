"""Benchmark hierarchy registration and union construction."""

import itertools
import typing as ty

import pytest

import dynapydantic

from .common import (
    DiscriminatorField,
    Implementation,
    SubclassCount,
    UnionMode,
    build_class_hierarchy,
    idgen,
)

SUBCLASS_COUNTS = (5, 25, 100)


@pytest.mark.parametrize(
    "subclass_count",
    [SubclassCount(n) for n in SUBCLASS_COUNTS],
    ids=idgen,
)
@pytest.mark.parametrize(
    ("implementation", "union_mode", "realization", "inject"),
    [
        pytest.param(
            Implementation.DYNAPYDANTIC,
            UnionMode.DISCRIMINATED,
            realization,
            inject,
        )
        for realization, inject in itertools.product(
            [
                dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
                dynapydantic.UnionRealization.VALIDATION,
            ],
            [DiscriminatorField.EXPLICIT, DiscriminatorField.INJECTED],
        )
    ]
    + [
        pytest.param(
            Implementation.DYNAPYDANTIC,
            UnionMode.SMART,
            dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
            None,
        ),
        pytest.param(
            Implementation.DYNAPYDANTIC,
            UnionMode.SMART,
            dynapydantic.UnionRealization.VALIDATION,
            None,
        ),
        pytest.param(Implementation.MANUAL, UnionMode.DISCRIMINATED, None, None),
        pytest.param(Implementation.MANUAL, UnionMode.SMART, None, None),
    ],
    ids=idgen,
)
def test_registration(  # noqa: PLR0913
    *,
    benchmark: ty.Any,  # noqa: ANN401 - could come from codspeed or benchmark
    subclass_count: int,
    implementation: Implementation,
    union_mode: UnionMode,
    realization: dynapydantic.UnionRealization | None,
    inject: DiscriminatorField | None,
) -> None:
    """Benchmark fresh hierarchy registration and union construction.

    Parameters
    ----------
    benchmark
        Pytest-benchmark fixture used to measure the operation.
    subclass_count
        Number of concrete subclasses to generate.
    implementation
        Implementation used to construct the hierarchy.
    union_mode
        Union mode used by the generated hierarchy.
    realization
        Dynapydantic union realization strategy, when applicable.
    inject
        Discriminator field strategy, when applicable.
    """
    benchmark.pedantic(
        build_class_hierarchy,
        kwargs={
            "subclass_count": subclass_count,
            "implementation": implementation,
            "union_mode": union_mode,
            "realization": realization,
            "inject": inject,
        },
        iterations=1,
        rounds=250,
        warmup_rounds=1,
    )
