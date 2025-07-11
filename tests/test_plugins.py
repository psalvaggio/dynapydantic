"""Test the plugin functionality"""

import importlib.metadata
import math
import pathlib
from unittest.mock import patch

import pydantic
import pytest


def setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the plugin example works"""
    d = pathlib.Path(__file__).parent
    # Put our example into the PYTHONPATH
    for pkg in ("base-package", "animal-plugins", "shape-plugins"):
        monkeypatch.syspath_prepend(d / "example" / pkg)

    # Mock out the entrypoints that are in the pyproject.toml's
    animal_ep = importlib.metadata.EntryPoint(
        name="animal-plugins",
        value="animal_plugins",
        group="animal.plugins",
    )
    shape_ep = importlib.metadata.EntryPoint(
        name="shape-plugins",
        value="shape_plugins.registration:register_models",
        group="shape.plugins",
    )

    with patch("importlib.metadata.entry_points") as mock_entry_points:

        class MockEps:
            def select(self, group: str) -> list[importlib.metadata.EntryPoint]:
                match group:
                    case "animal.plugins":
                        return [animal_ep]
                    case "shape.plugins":
                        return [shape_ep]
                return []

        mock_entry_points.return_value = MockEps()

        # import while the mocks are in place
        import base_package  # noqa: F401, PLC0415


@pytest.mark.parametrize(
    ("animal_json", "result"),
    [
        ('{"type": "Cat", "name": "Kitty"}', "Kitty says meow"),
        ('{"type": "Dog", "bark_volume": 100}', "WOOF"),
        ('{"type": "Horse"}', "neigh"),
    ],
)
def test_animal_subclasses(
    animal_json: str,
    result: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the plugin example works"""
    setup_env(monkeypatch)

    import base_package  # noqa: PLC0415

    class Parse(pydantic.RootModel):
        root: base_package.Animal.union()

    x = Parse.model_validate_json(animal_json).root
    assert x.speak() == result


@pytest.mark.parametrize(
    ("shape_json", "result"),
    [
        ('{"type": "Rect", "width": 5, "length": 10}', 50),
        ('{"type": "Square", "side": 5}', 25),
        ('{"type": "Circle", "radius": 1}', math.pi),
        ('{"type": "Triangle", "base": 5, "height": 4}', 10),
    ],
)
def test_shape_subclasses(
    shape_json: str,
    result: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the plugin example works"""
    setup_env(monkeypatch)

    import base_package  # noqa: PLC0415

    class Parse(pydantic.RootModel):
        root: base_package.Shape.union()

    x = Parse.model_validate_json(shape_json).root
    assert x.area() == pytest.approx(result, abs=1e-10)
