"""Version checking utilities."""

import pydantic


def pydantic_le(version: tuple[int, ...]) -> bool:
    """Test whether the pydantic version is <= ``version``."""
    return _pydantic_version() <= version


def pydantic_lt(version: tuple[int, ...]) -> bool:
    """Test whether the pydantic version is < ``version``."""
    return _pydantic_version() < version


def pydantic_ge(version: tuple[int, ...]) -> bool:
    """Test whether the pydantic version is >= ``version``."""
    return _pydantic_version() >= version


def pydantic_gt(version: tuple[int, ...]) -> bool:
    """Test whether the pydantic version is > ``version``."""
    return _pydantic_version() > version


_PYDANTIC_VERSION: tuple[int, ...] | None = None


def _pydantic_version() -> tuple[int, ...]:
    global _PYDANTIC_VERSION  # noqa: PLW0603

    if _PYDANTIC_VERSION is None:
        _PYDANTIC_VERSION = tuple(int(x) for x in pydantic.__version__.split("."))

    return _PYDANTIC_VERSION
