"""Benchmarks for validating polymorphic payloads"""

import json

import pydantic
import pytest
from pytest_codspeed import BenchmarkFixture

from . import helpers


@pytest.mark.parametrize("n_models", [8, 64])
def test_validate_python_model_construction(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Validating Python payloads with model-construction-time realization"""
    base = helpers.discriminated_base()
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = helpers.payloads(models)

    def run() -> list[pydantic.BaseModel]:
        """Validate every payload"""
        return [container.model_validate(payload) for payload in data]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_validate_python_validation_time(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Validating Python payloads with validation-time union realization"""
    base = helpers.discriminated_base(union_realization="validation")
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = helpers.payloads(models)

    def run() -> list[pydantic.BaseModel]:
        """Validate every payload"""
        return [container.model_validate(payload) for payload in data]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_validate_json_model_construction(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Validating JSON payloads with model-construction-time realization"""
    base = helpers.discriminated_base()
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = [json.dumps(payload) for payload in helpers.payloads(models)]

    def run() -> list[pydantic.BaseModel]:
        """Validate every payload"""
        return [container.model_validate_json(payload) for payload in data]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_validate_json_validation_time(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Validating JSON payloads with validation-time union realization

    This path re-encodes the field before handing it to the nested adapter,
    which makes it noticeably more expensive than the Python path.
    """
    base = helpers.discriminated_base(union_realization="validation")
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = [json.dumps(payload) for payload in helpers.payloads(models)]

    def run() -> list[pydantic.BaseModel]:
        """Validate every payload"""
        return [container.model_validate_json(payload) for payload in data]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("union_mode", ["smart", "left_to_right"])
def test_validate_python_non_discriminated(
    benchmark: BenchmarkFixture,
    union_mode: str,
) -> None:
    """Validating Python payloads through a non-discriminated union"""
    n_models = 8
    base = helpers.plain_base(union_mode)
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    data = helpers.payloads(models, discriminated=False)

    def run() -> list[pydantic.BaseModel]:
        """Validate every payload"""
        return [container.model_validate(payload) for payload in data]

    result = benchmark(run)
    assert len(result) == n_models


@pytest.mark.parametrize("n_models", [8, 64])
def test_construct_polymorphic_instances(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Constructing container models from already-built subclass instances"""
    base = helpers.discriminated_base()
    models = helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)
    items = [
        model(**{f"field_{i}": i, "label": f"label-{i}"})
        for i, model in enumerate(models)
    ]

    def run() -> list[pydantic.BaseModel]:
        """Build one container per instance"""
        return [container(item=item) for item in items]

    result = benchmark(run)
    assert len(result) == n_models
