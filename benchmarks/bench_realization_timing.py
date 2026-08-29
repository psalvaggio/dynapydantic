"""Compare union realization strategies and recursive validation.

The realization benchmarks separate *when* dynapydantic pays to assemble a
union from *how* that union validates.  ``immediate`` constructs the union
explicitly before the model is defined, ``model-construction`` resolves it
while Pydantic builds the model schema, and ``validation`` checks the registry
generation and resolves the current union through a cached nested
``TypeAdapter`` on every validation.  Setup is outside the timed call for all
three cases.

Use ``validation`` versus ``model-construction`` to estimate the incremental
validation-time dispatch cost.  Use the incremental rebuild benchmark when
you want to quantify the cost of keeping a construction-time schema current
as subclasses arrive; it is a registration/rebuild workload, not request
validation.  Results are most useful as ratios at the same subclass count
and payload shape.
"""

import typing as ty

import pydantic
import pytest
from pytest_codspeed.plugin import BenchmarkFixture

import dynapydantic


def _base(realization: str | None = None) -> type[dynapydantic.SubclassTrackingModel]:
    if realization is None:

        class Base(
            dynapydantic.SubclassTrackingModel,
            discriminator_field="type",
            discriminator_value_generator=lambda cls: cls.__name__,
        ):
            pass

    else:

        class Base(
            dynapydantic.SubclassTrackingModel,
            discriminator_field="type",
            discriminator_value_generator=lambda cls: cls.__name__,
            union_realization=realization,
        ):
            pass

    return Base


def _populate(base: type[dynapydantic.SubclassTrackingModel], size: int) -> None:
    for index in range(size):
        pydantic.create_model(f"Realized{index}", __base__=base, value=(int, index))


@pytest.mark.parametrize(
    "realization", ["immediate", "model-construction", "validation"]
)
def test_one_shot_validation(benchmark: BenchmarkFixture, realization: str) -> None:
    """Compare one validation after 50 subclasses have been registered.

    The timed operation is only ``Model.model_validate``.  The meaningful
    validation-time-union comparison is ``validation / model-construction``:
    values above 1 indicate extra per-validation overhead, while values near
    1 indicate that the dispatch cost is small relative to Pydantic's own
    validation work.  ``immediate`` is a useful lower-level reference for
    explicit union construction, but it is not a manual-library baseline.
    """
    base = _base(None if realization == "immediate" else realization)
    _populate(base, 50)
    annotation = (
        dynapydantic.Union[base]
        if realization == "immediate"
        else dynapydantic.Polymorphic[base]
    )

    class Model(pydantic.BaseModel):
        value: annotation

    payload = {"value": {"type": "Realized49", "value": 49}}
    benchmark(Model.model_validate, payload)


def test_incremental_rebuild(benchmark: BenchmarkFixture) -> None:
    """Measure registration plus schema rebuild after each new subclass.

    This intentionally includes the repeated ``model_rebuild`` calls and is
    not comparable with the one-shot validation timings.  It represents an
    application that discovers subclasses incrementally while using
    construction-time unions.
    """
    base = _base()
    subclasses = [
        pydantic.create_model(f"Incremental{index}", __base__=base, value=(int, index))
        for index in range(50)
    ]
    base.__DYNAPYDANTIC__.models.clear()
    base.__DYNAPYDANTIC__._generation = 0
    base.__DYNAPYDANTIC__.register_model(subclasses[0])

    class Model(pydantic.BaseModel):
        value: dynapydantic.Polymorphic[base]

    def rebuild_incrementally() -> None:
        for subclass in subclasses[1:]:
            base.__DYNAPYDANTIC__.register_model(subclass)
            Model.model_rebuild(force=True)

    benchmark(rebuild_incrementally)


@pytest.mark.parametrize("depth", [1, 5, 20])
def test_recursive_validation(benchmark: BenchmarkFixture, depth: int) -> None:
    """Validate recursive nesting to show per-level validation-time cost.

    Compare depths by slope: a roughly linear increase indicates recurring
    adapter/union work at each nested level.  This benchmark uses a smart
    union and is separate from the realization-mode comparison above.
    """

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base, extra="forbid"):
        value: int

    class B(Base, extra="forbid"):
        other: dynapydantic.Polymorphic[Base]

    B.model_rebuild(force=True)
    payload: dict[str, ty.Any] = {"value": 2}
    for _ in range(depth):
        payload = {"other": payload}
    benchmark(B.model_validate, payload)
