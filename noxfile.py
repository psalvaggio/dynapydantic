"""Nox sessions for the supported Python and Pydantic versions."""

from __future__ import annotations

import nox

PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
PYDANTIC_VERSIONS = tuple(f"2.{minor}" for minor in range(8, 14))


def pydantic_versions_for(python_version: str) -> tuple[str, ...]:
    """Return the Pydantic versions supported by a Python version."""
    if python_version == "3.14":  # 3.14 support was first added in 2.12
        return ("2.12", "2.13")
    return PYDANTIC_VERSIONS


def make_test_session(python_version: str, pydantic_version: str) -> None:
    """Register one isolated Python/Pydantic test session."""

    @nox.session(
        name=f"test-{python_version}-{pydantic_version}",
        python=python_version,
        venv_backend="uv",
    )
    def test(session: nox.Session) -> None:
        session.install(
            ".",
            f"pydantic=={pydantic_version}",
            "pytest>=8.4.1",
            "pytest-cov>=6.2.1",
        )
        session.run("pytest", *session.posargs)


for _python_version in PYTHON_VERSIONS:
    for _pydantic_version in pydantic_versions_for(_python_version):
        make_test_session(_python_version, _pydantic_version)
