"""Benchmarks for building unions, type adapters and polymorphic schemas"""

import pydantic
import pytest
from pytest_codspeed import BenchmarkFixture

import dynapydantic

from . import helpers


@pytest.mark.parametrize("n_models", [8, 64])
def test_discriminated_union(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Building the annotated discriminated union of a tracking group"""
    base = helpers.discriminated_base()
    helpers.add_subclasses(base, n_models)

    result = benchmark(dynapydantic.union, base)
    assert result is not None


@pytest.mark.parametrize("n_models", [8, 64])
def test_plain_union(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Building the plain union of a tracking group"""
    base = helpers.plain_base()
    helpers.add_subclasses(base, n_models)

    def run() -> object:
        """Build the plain union"""
        return dynapydantic.union(base, plain=True)

    result = benchmark(run)
    assert result is not None


@pytest.mark.parametrize("n_models", [8, 64])
def test_type_adapter_build(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Building the pydantic TypeAdapter for the tracked union

    This is the schema-generation cost paid the first time a union is
    validated with validation-time realization.
    """
    base = helpers.discriminated_base()
    helpers.add_subclasses(base, n_models)

    def run() -> pydantic.TypeAdapter:
        """Build a type adapter over the union"""
        return pydantic.TypeAdapter(dynapydantic.union(base))

    adapter = benchmark(run)
    assert adapter is not None


@pytest.mark.parametrize("n_models", [8, 64])
def test_polymorphic_field_schema(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Declaring a model with a `Polymorphic` field

    This measures the schema generation triggered by the
    model-construction-time union realization.
    """
    base = helpers.discriminated_base()
    helpers.add_subclasses(base, n_models)

    def run() -> type[pydantic.BaseModel]:
        """Declare the container model"""
        return helpers.container_model(base)

    container = benchmark(run)
    assert container is not None


@pytest.mark.parametrize("n_models", [8, 64])
def test_json_schema_generation(benchmark: BenchmarkFixture, n_models: int) -> None:
    """Generating the JSON schema of a model with a polymorphic field"""
    base = helpers.discriminated_base()
    helpers.add_subclasses(base, n_models)
    container = helpers.container_model(base)

    def run() -> dict:
        """Generate the JSON schema"""
        return container.model_json_schema()

    schema = benchmark(run)
    assert "properties" in schema


@pytest.mark.parametrize("n_models", [8, 64])
def test_model_rebuild_after_registration(
    benchmark: BenchmarkFixture,
    n_models: int,
) -> None:
    """Rebuilding tracked models after new registrations

    Models using model-construction-time realization need a rebuild when
    models are registered after the schema was built, e.g. with plugins.
    """
    base = helpers.discriminated_base()
    models = helpers.add_subclasses(base, n_models)

    def run() -> None:
        """Force a rebuild of every tracked model"""
        for model in models:
            model.model_rebuild(force=True)

    benchmark(run)
