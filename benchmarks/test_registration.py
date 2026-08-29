"""Benchmarks for declaring and registering tracked models"""

import typing as ty

import pydantic
import pytest
from pytest_codspeed import BenchmarkFixture

import dynapydantic

from . import helpers


def _literal(value: str) -> ty.Any:  # noqa: ANN401 (type is determined at runtime)
    """Build a `Literal` annotation for a runtime value

    Parameters
    ----------
    value
        The literal value

    Returns
    -------
    Any
        The annotation
    """
    return ty.Literal[value]  # type: ignore[not-a-type]


@pytest.mark.parametrize("n_models", [8, 64])
def test_declare_discriminated_subclasses(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Declaring tracked subclasses of a discriminated base model

    This covers the subclass hook, the tracking group setup and the injection
    of the discriminator field into every subclass.
    """

    def run() -> list[type[dynapydantic.SubclassTrackingModel]]:
        """Declare a fresh hierarchy"""
        return helpers.add_subclasses(helpers.discriminated_base(), n_models)

    models = benchmark(run)
    assert len(models) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_declare_plain_subclasses(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Declaring tracked subclasses of a non-discriminated base model"""

    def run() -> list[type[dynapydantic.SubclassTrackingModel]]:
        """Declare a fresh hierarchy"""
        return helpers.add_subclasses(helpers.plain_base(), n_models)

    models = benchmark(run)
    assert len(models) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_tracking_group_register(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Registering standalone pydantic models into a TrackingGroup

    This is the explicit registration path used by plugins, where models are
    not subclasses of the tracked base model.
    """
    models = [
        pydantic.create_model(
            f"Standalone{i}",
            type=(_literal(f"value-{i}"), f"value-{i}"),
            value=(int, ...),
        )
        for i in range(n_models)
    ]

    def run() -> dynapydantic.TrackingGroup:
        """Register every model into a fresh tracking group"""
        group = dynapydantic.TrackingGroup(
            name="benchmark-group",
            discriminator_field="type",
        )
        for model in models:
            group.register(model)
        return group

    group = benchmark(run)
    assert len(dynapydantic.registered_models(group)) == n_models
