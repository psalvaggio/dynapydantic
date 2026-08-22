"""Unit tests for pydantic version checking utilities."""

import re
from unittest import mock

import pydantic

from dynapydantic import version_check


def test_pydantic_version_has_major_minor_patch() -> None:
    """The installed pydantic version is a major.minor.patch version."""
    assert hasattr(pydantic, "__version__")
    assert re.fullmatch(r"\d+\.\d+\.\d+", pydantic.__version__)


def test_version_comparisons_use_pydantic_version() -> None:
    """Comparison helpers parse and compare the pydantic version."""
    with (
        mock.patch.object(pydantic, "__version__", "2.3.4"),
        mock.patch.object(version_check, "_PYDANTIC_VERSION", None),
    ):
        assert version_check.pydantic_le((2, 3, 4))
        assert version_check.pydantic_lt((2, 3, 5))
        assert version_check.pydantic_ge((2, 3, 4))
        assert version_check.pydantic_gt((2, 3, 3))
