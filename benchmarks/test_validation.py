"""Benchmark cold and steady-state polymorphic validation."""

import itertools
import typing as ty

import pydantic
import pytest

import dynapydantic

from .common import (
    DiscriminatorField,
    Implementation,
    PayloadCount,
    PayloadFormat,
    SubclassCount,
    UnionMode,
    build_class_hierarchy,
    idgen,
    make_payloads,
)


@pytest.mark.parametrize("subclass_count", [SubclassCount(10)], ids=idgen)
@pytest.mark.parametrize(
    ("implementation", "union_mode", "realization", "input_format"),
    [
        *[
            (
                Implementation.DYNAPYDANTIC,
                discriminated,
                realization,
                input_format,
            )
            for discriminated, realization, input_format in itertools.product(
                [UnionMode.DISCRIMINATED, UnionMode.SMART],
                [
                    dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
                    dynapydantic.UnionRealization.VALIDATION,
                ],
                [PayloadFormat.PYTHON, PayloadFormat.JSON],
            )
        ],
        *[
            (
                Implementation.MANUAL,
                discriminated,
                None,
                input_format,
            )
            for discriminated, input_format in itertools.product(
                [UnionMode.DISCRIMINATED, UnionMode.SMART],
                [PayloadFormat.PYTHON, PayloadFormat.JSON],
            )
        ],
    ],
    ids=idgen,
)
@pytest.mark.parametrize(
    "payload_count",
    [PayloadCount(i) for i in (1, 1000)],
    ids=idgen,
)
def test_validation(  # noqa: PLR0913
    *,
    benchmark: ty.Any,  # noqa: ANN401 - could come from codspeed or benchmark
    union_mode: UnionMode,
    implementation: Implementation,
    realization: dynapydantic.UnionRealization | None,
    input_format: PayloadFormat,
    subclass_count: SubclassCount,
    payload_count: PayloadCount,
) -> None:
    """Benchmark validation while excluding benchmark-case construction.

    The benchmark setup runs once per round but is excluded from the timed
    region. Each round gets a fresh tracking group, so the first validation
    includes one-time adapter construction, while a 1000-validation round can
    amortize that construction over the whole batch.

    Parameters
    ----------
    benchmark
        Pytest-benchmark fixture used to measure validation.
    union_mode
        Union mode used by the generated hierarchy.
    implementation
        Implementation used to construct the hierarchy.
    realization
        Dynapydantic union realization strategy, when applicable.
    input_format
        Format of the validation payloads.
    subclass_count
        Number of concrete subclasses in the generated hierarchy.
    payload_count
        Number of payloads validated in each benchmark iteration.
    """

    def _setup() -> tuple[tuple[ty.Any, ...], dict[str, ty.Any]]:
        model = build_class_hierarchy(
            subclass_count=subclass_count,
            implementation=implementation,
            union_mode=union_mode,
            realization=realization
            if realization is not None
            else dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
            inject=DiscriminatorField.EXPLICIT,
        )
        return (
            model,
            make_payloads(
                input_format,
                payload_count=payload_count,
                subclass_count=subclass_count,
            ),
        ), {}

    if input_format == PayloadFormat.JSON:

        def _run(model: type[pydantic.BaseModel], payloads: list[ty.Any]) -> None:
            _ = [model.model_validate_json(x) for x in payloads]

    else:

        def _run(model: type[pydantic.BaseModel], payloads: list[ty.Any]) -> None:
            _ = [model.model_validate(x) for x in payloads]

    benchmark.pedantic(
        _run,
        setup=_setup,
        rounds=100,
        iterations=1,
        warmup_rounds=0,
    )
