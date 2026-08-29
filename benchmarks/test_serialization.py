"""Benchmarks for serializing and round-tripping polymorphic models"""

import pydantic
import pytest
from pytest_codspeed import BenchmarkFixture

from . import helpers


def _built_containers(
    n_models: int,
    union_realization: str = "model-construction",
) -> tuple[type[pydantic.BaseModel], list[pydantic.BaseModel]]:
    """Build a container model and one instance per tracked subclass

    Parameters
    ----------
    n_models
        Number of tracked subclasses to declare
    union_realization
        When the union should be realized

    Returns
    -------
    tuple[type[pydantic.BaseModel], list[pydantic.BaseModel]]
        The container model and the built instances
    """
    base = helpers.discriminated_base(union_realization)
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = helpers.payloads(models)
    return container, [container.model_validate(payload) for payload in data]


@pytest.mark.parametrize("n_models", [8, 64])
def test_serialize_python(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Dumping polymorphic models to Python objects"""
    _, instances = _built_containers(n_models)

    def run() -> list[dict]:
        """Dump every instance"""
        return [instance.model_dump() for instance in instances]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_serialize_json(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Dumping polymorphic models to JSON"""
    _, instances = _built_containers(n_models)

    def run() -> list[str]:
        """Dump every instance"""
        return [instance.model_dump_json() for instance in instances]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_round_trip_json(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Serializing and re-validating polymorphic models through JSON"""
    container, instances = _built_containers(n_models)

    def run() -> list[pydantic.BaseModel]:
        """Round-trip every instance"""
        return [
            container.model_validate_json(instance.model_dump_json())
            for instance in instances
        ]

    result = benchmark(run)
    assert len(result) == n_models
