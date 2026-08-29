"""Synthetic entry-point plugin loading benchmark."""

import importlib.metadata
import sys
import types
import typing as ty
from unittest.mock import patch

import pydantic
import pytest
from pytest_codspeed.plugin import BenchmarkFixture

import dynapydantic


@pytest.fixture
def plugin_case(request: pytest.FixtureRequest):
    """Create N plugin entry points and patch entry-point discovery."""
    size = int(request.node.callspec.params["size"])
    group = dynapydantic.TrackingGroup(
        name=f"plugins-{size}", discriminator_field="type"
    )
    entry_points = []
    for index in range(size):
        model = pydantic.create_model(
            f"Plugin{index}",
            type=(
                ty.Literal[f"Plugin{index}"],  # type: ignore[invalid-literal]
                f"Plugin{index}",
            ),
            value=(int, index),
        )

        def register(model=model) -> None:
            group.register_model(model)

        module_name = f"benchmark_plugin_{size}_{index}"
        module = types.ModuleType(module_name)
        module.register = register  # type: ignore[attr-defined]
        sys.modules[module_name] = module
        entry_points.append(
            importlib.metadata.EntryPoint(
                name=f"plugin-{index}",
                value=f"{module_name}:register",
                group="benchmark.plugins",
            )
        )

    class EntryPoints:
        def select(self, *, group: str):
            return entry_points if group == "benchmark.plugins" else []

    with patch("importlib.metadata.entry_points", return_value=EntryPoints()):
        group.plugin_entry_point = "benchmark.plugins"
        yield group


@pytest.mark.parametrize("size", [1, 10, 50, 100, 500])
def test_load_plugins(benchmark: BenchmarkFixture, plugin_case, size: int) -> None:
    """Time loading N entry-point plugins."""
    benchmark(dynapydantic.load_plugins, plugin_case)
