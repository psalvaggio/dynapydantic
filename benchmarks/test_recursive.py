"""Benchmarks for recursive polymorphic model trees"""

import json
import typing as ty

import pydantic
import pytest
from pytest_codspeed import BenchmarkFixture

import dynapydantic

from . import helpers

DEPTH = 4
BRANCHING = 3


def _tree_models(
    union_realization: str,
) -> tuple[helpers.BaseT, type[pydantic.BaseModel]]:
    """Declare a recursive Node/Leaf hierarchy

    Parameters
    ----------
    union_realization
        When the union should be realized

    Returns
    -------
    tuple[type[dynapydantic.SubclassTrackingModel], type[pydantic.BaseModel]]
        The tracking base class and the recursive node model
    """
    base = helpers.discriminated_base(union_realization)
    pydantic.create_model("Leaf", __base__=base, value=(int, ...))
    node = pydantic.create_model(
        "Node",
        __base__=base,
        children=(list[dynapydantic.Polymorphic[base]], ...),
    )
    if union_realization != "validation":
        for model in dynapydantic.registered_models(base).values():
            model.model_rebuild(force=True)
    return base, node


def _tree_payload(depth: int) -> dict[str, ty.Any]:
    """Build a nested payload of the given depth

    Parameters
    ----------
    depth
        Remaining depth of the tree

    Returns
    -------
    dict
        The nested payload
    """
    if depth == 0:
        return {"type": "Leaf", "value": depth}
    return {
        "type": "Node",
        "children": [_tree_payload(depth - 1) for _ in range(BRANCHING)],
    }


@pytest.mark.parametrize(
    "union_realization",
    ["model-construction", "validation"],
)
def test_validate_recursive_python(
    benchmark: BenchmarkFixture,
    union_realization: str,
) -> None:
    """Validating a nested tree of polymorphic models from Python objects"""
    _, node = _tree_models(union_realization)
    payload = _tree_payload(DEPTH)

    def run() -> pydantic.BaseModel:
        """Validate the tree"""
        return node.model_validate(payload)

    result = benchmark(run)
    assert len(result.model_dump()["children"]) == BRANCHING


@pytest.mark.parametrize(
    "union_realization",
    ["model-construction", "validation"],
)
def test_validate_recursive_json(
    benchmark: BenchmarkFixture,
    union_realization: str,
) -> None:
    """Validating a nested tree of polymorphic models from JSON"""
    _, node = _tree_models(union_realization)
    payload = json.dumps(_tree_payload(DEPTH))

    def run() -> pydantic.BaseModel:
        """Validate the tree"""
        return node.model_validate_json(payload)

    result = benchmark(run)
    assert len(result.model_dump()["children"]) == BRANCHING


def test_serialize_recursive_json(benchmark: BenchmarkFixture) -> None:
    """Serializing a nested tree of polymorphic models to JSON"""
    _, node = _tree_models("model-construction")
    tree = node.model_validate(_tree_payload(DEPTH))

    def run() -> str:
        """Serialize the tree"""
        return tree.model_dump_json()

    result = benchmark(run)
    assert result.startswith("{")
