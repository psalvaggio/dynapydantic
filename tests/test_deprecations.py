"""Holds tests for any functionality that is currently deprecated"""

from unittest import mock

import pytest

import dynapydantic


def test_deprecated_union() -> None:
    """SubclassTrackingModel.union() is deprecated"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    with pytest.warns(DeprecationWarning, match="dynapydantic.union"):
        union = Base.union()

    assert union == dynapydantic.union(Base)
    assert union == dynapydantic.Union[Base]


def test_deprecated_load_plugins() -> None:
    """SubclassTrackingModel.load_plugins() is deprecated"""

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        plugin_entry_point="base.plugins",
    ):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    with (
        mock.patch.object(
            dynapydantic.TrackingGroup, "load_plugins", return_value=None
        ) as mock_lp,
        pytest.warns(DeprecationWarning, match="dynapydantic.load_plugins"),
    ):
        Base.load_plugins()

    mock_lp.assert_called_once_with()


def test_deprecated_registered_subclasses() -> None:
    """SubclassTrackingModel.registered_subclasses() is deprecated"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    with pytest.warns(DeprecationWarning, match="dynapydantic.registered_models"):
        models = Base.registered_subclasses()

    assert models == dynapydantic.registered_models(Base)
