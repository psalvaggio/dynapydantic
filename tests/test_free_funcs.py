"""Unit tests for the free function API"""

from unittest import mock

import pydantic
import pytest

import dynapydantic

# ------ union() ---------------------------------------------------------------


def test_union_tg() -> None:
    """Test union on a TrackingGroup"""
    group = dynapydantic.TrackingGroup(name="test", union_mode="smart")

    @group.register
    class A(pydantic.BaseModel):
        a: int

    @group.register
    class B(pydantic.BaseModel):
        b: int

    assert dynapydantic.union(group) == A | B

    with mock.patch.object(
        dynapydantic.TrackingGroup, "union", autospec=True
    ) as mock_union:
        dynapydantic.union(group)

    mock_union.assert_called_once_with(group, plain=None)


def test_union_stm() -> None:
    """Test union on a SubclassTrackingModel"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    assert dynapydantic.union(Base) == A | B

    with mock.patch.object(
        dynapydantic.TrackingGroup, "union", autospec=True
    ) as mock_union:
        dynapydantic.union(Base)

    mock_union.assert_called_once_with(Base.__DYNAPYDANTIC__, plain=None)


def test_union_other() -> None:
    """Test union raises with a bad argument"""
    with pytest.raises(TypeError):
        dynapydantic.union("foo")  # type: ignore[bad-argument-type]


# ------ load_plugins() --------------------------------------------------------


def test_load_plugins_tg() -> None:
    """Test load_plugins on a TrackingGroup"""
    group = dynapydantic.TrackingGroup(name="test", union_mode="smart")

    @group.register
    class A(pydantic.BaseModel):
        a: int

    with mock.patch.object(
        dynapydantic.TrackingGroup, "load_plugins", autospec=True
    ) as mock_lp:
        dynapydantic.load_plugins(group)

    mock_lp.assert_called_once_with(group)


def test_load_plugins_stm() -> None:
    """Test load_plugins on a SubclassTrackingModel"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    with mock.patch.object(
        dynapydantic.TrackingGroup, "load_plugins", autospec=True
    ) as mock_lp:
        dynapydantic.load_plugins(Base)

    mock_lp.assert_called_once_with(Base.__DYNAPYDANTIC__)


def test_load_plugins_other() -> None:
    """Test union raises with a bad argument"""
    with pytest.raises(TypeError):
        dynapydantic.load_plugins("foo")  # type: ignore[bad-argument-type]


# ------ registered_models() ---------------------------------------------------


def test_registered_models_tg() -> None:
    """Test registered_models on a TrackingGroup"""
    group = dynapydantic.TrackingGroup(name="test", union_mode="smart")

    @group.register
    class A(pydantic.BaseModel):
        a: int

    @group.register
    class B(pydantic.BaseModel):
        b: int

    assert set(dynapydantic.registered_models(group).values()) == {A, B}

    placeholder = object()
    with mock.patch.object(group, "models", new=placeholder):
        assert dynapydantic.registered_models(group) is placeholder


def test_registered_models_stm() -> None:
    """Test union on a SubclassTrackingModel"""

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base):
        a: int

    class B(Base):
        b: int

    assert set(dynapydantic.registered_models(Base).values()) == {A, B}

    placeholder = object()
    with mock.patch.object(Base.__DYNAPYDANTIC__, "models", new=placeholder):
        assert dynapydantic.registered_models(Base) is placeholder


def test_registered_models_other() -> None:
    """Test registered_models raises with a bad argument"""
    with pytest.raises(TypeError):
        dynapydantic.registered_models("foo")  # type: ignore[bad-argument-type]
