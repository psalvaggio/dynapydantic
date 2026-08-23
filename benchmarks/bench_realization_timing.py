"""Compare union realization strategies and recursive validation."""

import typing as ty

import pydantic
import pytest

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
def test_one_shot_validation(benchmark, realization: str) -> None:
    """Compare validation after 50 subclasses have been registered."""
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


def test_incremental_rebuild(benchmark) -> None:
    """Rebuild a construction-time schema after each incremental registration."""
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
def test_recursive_validation(benchmark, depth: int) -> None:
    """Validate the recursive B.other example at several nesting depths."""

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
